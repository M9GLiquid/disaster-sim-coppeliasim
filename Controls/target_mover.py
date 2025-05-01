class TargetMover:
    def __init__(self, sim):
        self.sim = sim
        self.target = self.sim.getObject('/target')

        self.current_velocity = [0.0, 0.0, 0.0]  # dx, dy, dz
        self.current_yaw_rate = 0.0  # radians/sec

        self.response_speed = 10.0  # Higher = more aggressive response

    def update(self, desired_velocity, desired_yaw_rate, dt):
        sim = self.sim
        # Assuming caller holds the simulation lock
        pos = sim.getObjectPosition(self.target, -1)
        ori = sim.getObjectOrientation(self.target, -1)

        # Simple inertia model: move current velocity toward desired velocity
        for i in range(3):
            delta = desired_velocity[i] - self.current_velocity[i]
            self.current_velocity[i] += delta * min(self.response_speed * dt, 1.0)

        delta_yaw = desired_yaw_rate - self.current_yaw_rate
        self.current_yaw_rate += delta_yaw * min(self.response_speed * dt, 1.0)

        new_pos = [
            pos[0] + self.current_velocity[0] * dt,
            pos[1] + self.current_velocity[1] * dt,
            pos[2] + self.current_velocity[2] * dt
        ]
        new_ori = [
            ori[0],
            ori[1],
            ori[2] + self.current_yaw_rate * dt
        ]

        sim.setObjectPosition(self.target, -1, new_pos)
        sim.setObjectOrientation(self.target, -1, new_ori)
