---
applyTo: "**/commit-msg"
---

# Commit Instructions

## Commit Process

- Follow these steps IN ORDER:

1. **Prepare CHANGELOG.md (Part 1)**:
   - Ensure all changes are documented under **[UNRELEASED]** section
   - Replace `## [UNRELEASED]` with `## [V.X.Y.Z] - YYYY-MM-DD` using correct version and today's date
   - Verify formatting and categorization follow guidelines

2. **Stage all files**: `git add .`

3. **Commit with proper message format**:
   ```
   git commit -m "[V.X.Y.Z] - YYYY-MM-DD Title of changes" -m "
   - Added: Description of new features 
   - Changed: Description of changes 
   - Fixed: Description of bug fixes
   "
   ```
   - Ensure commit message format matches version number in CHANGELOG.md

## Commit Message Format

- **First line**: `[V.X.Y.Z] - YYYY-MM-DD Title of commit`
- **Blank line**
- **Bulleted list** with prefixed categories

## Common Errors to Avoid

- DO NOT include multiple version numbers in commit message
- DO NOT forget the date in YYYY-MM-DD format
- DO NOT use generic commit messages like "Fix" or "Update"
- DO NOT push before adding new Unreleased section to CHANGELOG.md
- DO NOT proceed to pushing without verifying commit and amended CHANGELOG.md

## Versioning Rules

**Format**: `V.X.Y.Z`
- **X**: Major (breaking changes)
- **Y**: Minor (new features)
- **Z**: Patch (bug fixes)

Example: V.0.11.0 represents a minor release with new features, but no breaking changes.
