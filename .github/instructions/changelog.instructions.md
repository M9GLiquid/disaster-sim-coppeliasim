---
applyTo: "**/CHANGELOG.md"
---

# Changelog Instructions

## Managing CHANGELOG.md

- Document ALL changes under the `## [Unreleased]` section at the top of CHANGELOG.md.
- Organize changes under these specific headers:
  - ### Added
    - New features or capabilities that didn't exist before
  - ### Improved
    - Enhancements to existing features without changing core functionality
  - ### Changed
    - Modifications to existing behavior or implementation
  - ### Fixed
    - ONLY bugs from previous versions, not issues introduced in the current version
  - ### Removed
    - Features or functionality deliberately taken out

## Categorization Guidelines

- **Added**: New features that didn't exist before
- **Improved**: Making existing features better without changing behavior
- **Changed**: Altering existing behavior
- **Fixed**: Only bugs from previous versions
- **Removed**: Features deliberately taken out

## Common Errors to Avoid

- DO NOT create multiple version headers for the same release
- DO NOT duplicate content between Unreleased and versioned sections
- DO NOT list bug fixes for issues introduced in the current version
- DO NOT use vague descriptions like "Fixed various bugs"
- DO NOT mix improvements with changes
