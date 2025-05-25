---
applyTo: "**/push*.md,**/git-push*.md"
---

# Push Instructions

## Push Process

IMPORTANT: This process should ONLY be started after completing all steps in the Changelog and Commit guides.
Pushing requires explicit authorization.

1. **Update `README.md` if necessary**:
   - Review README.md to see if it needs updating based on recent changes
   - Consider what's in the latest Changelog and whether README should reflect these changes
   - Ensure README accurately reflects your recent changes

2. **Amend README changes if needed**:
   ```
   git add README.md
   ```
   - Verify changes are committed

3. **Check if pushing is authorized**:
   - Verify that you have explicit authorization to push these changes
   - Confirm that it's appropriate to push at this time

4. **Push to remote**:
   ```
   git push
   ```
   - Confirm push was successful
   - This step should ONLY be done with explicit authorization!

## Common Errors to Avoid

- DO NOT push automatically after committing
- DO NOT push without reviewing changes one last time
- DO NOT push if you don't have authorization
- DO NOT force push unless absolutely necessary and you understand the consequences

## Pre-Push Checklist

Before pushing, ask yourself:
- Have I completed all steps in the Changelog Guide?
- Have I followed all steps in the Commit Guide?
- Is README.md up-to-date with the latest changes?
- Do I have authorization to push these changes?
