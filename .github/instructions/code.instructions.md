---
applyTo: "**/*.py"
---

# Coding Instructions

## Important Notes
- **NEVER** use `print()` for debugging, use `logging` module instead
- The CoppeliaSim API is not thread-safe, so **NEVER** use it in a separate thread
- The CoppeliaSim is calling over RPC, so **NEVER** use try catch when dealing with `sim.` calls.
- Should work work for MacOs and windows, so **NEVER** use platform-specific code
- **IMPORTANT** If you encounter a inline issue and it can't be fixed first try. Stop and ask the user for help.

## General Principles

- Understand intent before implementing
- You are a Python expert
- Explain intended actions to user
- Avoid redundancy and assumptions
- Favor clarity over brevity
- Ask when uncertain
- Don't keep backward compatibility
- Apply patterns responsibly
- Don't do defensive programming
- Try to resolve issues properly
- **NEVER** use defencive programming (investigate the issue instead or ask for help)
- **ALWAYS** Remove dead and unused code.

## Documentation & API Usage

- ONLY for codebase. Not External Tools
- Check local docs before coding against coppeliasim API: `Docs/en/` (`Docs/en/apiFunctions.htm`, `Docs/en/propertiesReference.htm`)
- **STRICT API RULE**: Only use functions documented in `Docs/en/apiFunctions.htm`
- Project uses CoppeliaSim 4.9+
- Verify functions against current docs - API differs from older versions

## Naming Conventions

- Files: `snake_case`
- Classes: `CamelCase`
- Folders: `PascalCase`
- Group related helpers logically

## Architectural Patterns

### Singleton Pattern
- Only for Codebase, Not External Tools
- Access via `get_instance()`, never instantiate directly
- Key singletons: `EventManager`, `KeyboardManager`, `SimConnection`
- Don't create new unless really needed

### Publisher-Subscriber Pattern
- Only for Codebase, Not External Tools
- Use for decoupling components
- Use event system for inter-component communication
- Components should not directly call methods of unrelated components
- Subscribe to events rather than polling for changes

### Separation of Concerns (SoC)
- One responsibility per module
- Keep classes focused on a single task
- Separate UI, business logic, and data processing
- Use managers to coordinate between subsystems

### DRY (Don't Repeat Yourself)
- Extract common functionality into utility functions
- Create reusable components
- Avoid copy-pasted code blocks

## Code Style

- Composition over inheritance
- Clear naming, avoid deep nesting
- Keep methods small and focused
- Document complex algorithms
- Write unit tests for critical components
- No excess documentation