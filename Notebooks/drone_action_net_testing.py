import os
import numpy as np
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

# --- CONFIG ---
split = 'test'  # 'val' or 'train' for confusion matrix; 'test' for final benchmark
data_dir = f'/content/drive/MyDrive/AI for Robotics/Disaster Simulator/depth_dataset/{split}'
model_checkpoint = '/content/drive/MyDrive/AI for Robotics/models/drone_action_net_epoch_80.pth'
sequence_length = 10  # Must match your model
action_names = ['Right', 'Left', 'Forward', 'Backward', 'Up', 'Down', 'Left Yaw', 'Right Yaw', 'Hover']
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ---(1) Data Loading---
def load_data(data_dir):
    all_images = []
    all_victims = []
    all_fnames = []
    for npz_file in sorted([f for f in os.listdir(data_dir) if f.endswith('.npz')]):
        file_path = os.path.join(data_dir, npz_file)
        data = np.load(file_path)
        if 'depths' in data and 'victim_dirs' in data:
            depths = data['depths']
            victim_dirs = data['victim_dirs']
            if victim_dirs.shape[1] == 3:
                dist = np.linalg.norm(victim_dirs, axis=1, keepdims=True)
                victim_dirs = np.concatenate([victim_dirs, dist], axis=1)
            all_images.extend(depths)
            all_victims.extend(victim_dirs)
            all_fnames.extend([npz_file]*len(depths))
    return np.array(all_images), np.array(all_victims), all_fnames

# ---(2) Episode Segmentation---
def find_episodes_by_victim_dir(victim_dirs, min_episode_length=10):
    distances = victim_dirs[:, 3]
    boundaries = []
    N = len(distances)
    start = 0
    while start < N:
        window_end = min(start + 500, N) # Max 500 frames per episode
        end = start + np.argmin(distances[start:window_end])
        if end - start >= min_episode_length:
            boundaries.append((start, end))
        start = end + 1
    return boundaries

def plot_episode_boundaries(distances, boundaries):
    plt.figure(figsize=(15,5))
    plt.plot(distances, label='Victim Dir Norm (distance)')
    for (s, e) in boundaries:
        plt.axvspan(s, e, color='orange', alpha=0.15)
    plt.xlabel('Frame Index')
    plt.ylabel('Distance to Victim')
    plt.title('Victim Dir Distance and Detected Episode Boundaries')
    plt.legend()
    plt.show()

# ---(3) Model Definition & Loading---
import timm
import torch.nn as nn
class ConvLSTMCell(nn.Module):
    def __init__(self, in_ch, hidden_ch, k=3):
        super().__init__()
        p = k // 2
        self.conv = nn.Conv2d(in_ch + hidden_ch, 4 * hidden_ch, k, padding=p)
        self.hidden_ch = hidden_ch
    def forward(self, x, h, c):
        combined = torch.cat([x, h], 1)
        gates = self.conv(combined)
        i, f, o, g = gates.chunk(4, 1)
        i, f, o = torch.sigmoid(i), torch.sigmoid(f), torch.sigmoid(o)
        g = torch.tanh(g)
        c = f * c + i * g
        h = o * torch.tanh(c)
        return h, c
class SimpleConvLSTM(nn.Module):
    def __init__(self, in_ch, hidden_ch, k=3):
        super().__init__()
        self.cell = ConvLSTMCell(in_ch, hidden_ch, k)
    def forward(self, x):
        B, T, C, H, W = x.shape
        h = torch.zeros(B, self.cell.hidden_ch, H, W, device=x.device)
        c = torch.zeros_like(h)
        outs = []
        for t in range(T):
            h, c = self.cell(x[:, t], h, c)
            outs.append(h)
        return torch.stack(outs, 1)
class DroneActionNet(nn.Module):
    def __init__(self, num_actions=9, vic_dim=4, backbone='mobilenetv3_small_100', hidden=32):
        super().__init__()
        self.backbone = timm.create_model(backbone, pretrained=True, features_only=True, in_chans=1)
        out_ch = self.backbone.feature_info[-1]['num_chs']
        self.lstm = SimpleConvLSTM(out_ch, hidden)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.vfc = nn.Linear(vic_dim, 16)
        self.fc = nn.Sequential(
            nn.Linear(hidden + 16, 64),
            nn.ReLU(),
            nn.Linear(64, num_actions)
        )
    def forward(self, x, vic):
        B, T, _, H, W = x.shape
        x = x.view(B * T, 1, H, W)
        feat = self.backbone(x)[-1]
        feat = feat.view(B, T, feat.size(1), feat.size(2), feat.size(3))
        out = self.lstm(feat)
        img = self.pool(out[:, -1]).view(B, -1)
        vic_feat = self.vfc(vic[:, -1])
        return self.fc(torch.cat([img, vic_feat], 1))
def load_model(model_checkpoint, device):
    checkpoint = torch.load(model_checkpoint, map_location=device)
    model = DroneActionNet().to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    return model

# ---(4) Ground Truth Loader---
def load_actions_for_frames(start, end, all_fnames, data_dir):
    gt = []
    frame_ptr = start
    while frame_ptr <= end:
        fname = all_fnames[frame_ptr]
        local_idx = 0
        for j in range(frame_ptr, end+1):
            if all_fnames[j] != fname:
                break
            local_idx += 1
        fpath = os.path.join(data_dir, fname)
        d = np.load(fpath)
        if 'actions' in d:
            gt.extend(list(d['actions'][:local_idx]))
        else:
            gt.extend([None]*local_idx)
        frame_ptr += local_idx
    return gt

# ---(5) Prediction and Analysis---
def predict_and_analyze(model, all_images, all_victims, all_fnames, boundaries, sequence_length, data_dir, split, action_names):
    all_predicted_actions = []
    all_prediction_times_ms = []
    all_ground_truth_actions = []
    all_episode_predicted = []
    import time
    for epi_idx, (s, e) in enumerate(boundaries):
        print(f"Processing Episode {epi_idx+1} ({e-s+1} frames):")
        episode_imgs = all_images[s:e+1]
        episode_vics = all_victims[s:e+1]
        episode_actions = load_actions_for_frames(s, e, all_fnames, data_dir)
        num_frames = len(episode_imgs)
        episode_preds = [None] * num_frames
        episode_pred_times = [None] * num_frames
        for frame_idx in range(sequence_length - 1, num_frames):
            start_idx = frame_idx - sequence_length + 1
            end_idx = frame_idx + 1
            model_in_x = torch.from_numpy(np.stack(episode_imgs[start_idx:end_idx])).unsqueeze(1).unsqueeze(0).float().to(device)
            model_in_v = torch.from_numpy(np.stack(episode_vics[start_idx:end_idx])).unsqueeze(0).float().to(device)
            py_start = time.time()
            with torch.no_grad():
                outputs = model(model_in_x, model_in_v)
            pred = outputs.argmax(1).cpu().numpy()[0]
            pred_time_ms = (time.time() - py_start) * 1000
            episode_preds[frame_idx] = pred
            episode_pred_times[frame_idx] = pred_time_ms
            all_predicted_actions.append(pred)
            all_prediction_times_ms.append(pred_time_ms)
            if episode_actions[frame_idx] is not None:
                all_ground_truth_actions.append(int(episode_actions[frame_idx]))
        all_episode_predicted.append([p for p in episode_preds if p is not None])
        print(f"Mean time per frame: {np.mean([t for t in episode_pred_times if t is not None]):.2f} ms")
    return all_predicted_actions, all_prediction_times_ms, all_ground_truth_actions

# ---(6) Timing and Metric Plots---
def plot_timing_and_metrics(all_prediction_times_ms):
    plt.figure(figsize=(12,6))
    plt.plot(all_prediction_times_ms, marker='.', label='Prediction Time (ms)')
    plt.axhline(33.33, color='red', linestyle='--', label='30 FPS Limit (33.3ms)')
    plt.axhline(16.67, color='orange', linestyle='--', label='60 FPS Limit (16.7ms)')
    plt.xlabel('Frame Index (all episodes)')
    plt.ylabel('Prediction Time (ms)')
    plt.title('Prediction Time per Frame (All Episodes)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    plt.figure(figsize=(8,4))
    plt.hist(all_prediction_times_ms, bins=25, color='skyblue', edgecolor='k')
    plt.xlabel('Prediction Time (ms)')
    plt.ylabel('Frame Count')
    plt.title('Distribution of Prediction Times')
    plt.tight_layout()
    plt.show()
    plt.figure(figsize=(8,4))
    sorted_times = np.sort(all_prediction_times_ms)
    cdf = np.arange(1, len(sorted_times)+1) / len(sorted_times)
    plt.plot(sorted_times, cdf, marker='.')
    plt.xlabel('Prediction Time (ms)')
    plt.ylabel('Cumulative Proportion')
    plt.title('CDF of Prediction Times')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    times = np.array(all_prediction_times_ms)
    print('--- Timing Statistics ---')
    print(f'Mean: {np.mean(times):.2f} ms, Median: {np.median(times):.2f} ms, Min: {np.min(times):.2f} ms, Max: {np.max(times):.2f} ms')
    print(f'95th percentile: {np.percentile(times, 95):.2f} ms, 99th percentile: {np.percentile(times, 99):.2f} ms')
    print(f'Effective FPS: {1000 / np.mean(times):.2f}')

# ---(7) Confusion Matrix---
def plot_confusion_matrix(all_ground_truth_actions, all_predicted_actions, action_names, split):
    if split in ['train', 'val'] and all_ground_truth_actions:
        cm = confusion_matrix(all_ground_truth_actions, all_predicted_actions)
        acc = accuracy_score(all_ground_truth_actions, all_predicted_actions)
        f1 = f1_score(all_ground_truth_actions, all_predicted_actions, average='weighted')
        print(f"Accuracy: {acc:.3f}, Weighted F1: {f1:.3f}")
        import seaborn as sns
        plt.figure(figsize=(8,6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=action_names, yticklabels=action_names)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix')
        plt.tight_layout()
        plt.show()
    elif split == 'test':
        print('Skipping confusion matrix: Not available for test set.')
    else:
        print("No ground truth available: skipping confusion matrix.")

# ---(8) Run All---
# You can run these individually in Colab, or just run all at once by running below cell:

def run_all():
    all_images, all_victims, all_fnames = load_data(data_dir)
    boundaries = find_episodes_by_victim_dir(all_victims)
    print(f"Detected {len(boundaries)} episodes:")
    for i, (s, e) in enumerate(boundaries):
        print(f"Episode {i+1}: frames {s} to {e} (len={e-s+1})")
    plot_episode_boundaries(all_victims[:,3], boundaries)
    model = load_model(model_checkpoint, device)
    all_predicted_actions, all_prediction_times_ms, all_ground_truth_actions = predict_and_analyze(
        model, all_images, all_victims, all_fnames, boundaries, sequence_length, data_dir, split, action_names)
    plot_timing_and_metrics(all_prediction_times_ms)
    plot_confusion_matrix(all_ground_truth_actions, all_predicted_actions, action_names, split)

# Uncomment to run all pipeline at once:
run_all()
