---
applyTo: "**/ROADMAP.md"
---

# Bug Tracking Instructions

- NEVER update ROADMAP.md to mark a bug as fixed without explicit user confirmation.
- ALL bug status changes require explicit user confirmation—no exceptions.
- Do not modify ROADMAP.md unless specifically instructed.

## When Bugs Are Reported

- Add new bugs to ROADMAP.md immediately with the next BUG-XX index.
- Include error messages, affected components, steps to reproduce, and impact.
- Format as: `- [ ] **BUG-XX:** [Description]—[Recommended fix]`
- Add [CRITICAL] tag for severe bugs impacting core functionality.
- Analyze and determine severity (Low, Medium, High, Critical).
- Inform user about the bug's addition to ROADMAP and probable cause.

## Handling Different Bug Types

- For non-critical bugs:
  - Ask "Would you like me to fix this bug now?" before implementing changes.
  - Wait for user confirmation.
- For critical bugs:
  - Inform: "This is a critical issue affecting core functionality. I'll fix it immediately."
  - Implement the fix, but DO NOT update ROADMAP until user confirms it works.

## Verification Process

- After implementing a fix, ask: "Has this bug been fixed to your satisfaction?"
- Wait for explicit confirmation (like "CONFIRM FIX").
- Present proposed ROADMAP changes in a code block.
- Only update ROADMAP after user approval with "UPDATE ROADMAP" command.
- If verification fails, treat as ongoing or new bug.

## Reference Order

- Maintain chronological order in ROADMAP.md.
- Consider interactions with other systems before implementing fixes.
- Reference MENU_REFACTOR_PLAN.md for UI-related bugs.
- Follow project coding standards for all fixes.
