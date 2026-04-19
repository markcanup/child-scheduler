# AGENTS.md

## Working agreements

- Read `PROJECT_BRIEF.md` and `TASKS.md` before starting work.
- Follow milestone order unless explicitly told otherwise.
- Do not change the Hubitat ↔ AWS contracts without updating docs.
- Prefer Python for backend implementation.
- Add tests for compiler behavior and endpoint validation.
- Do not run `npm install` or `npm ci` during normal execution; dependencies are preinstalled during setup.
- For UI changes, run build/test only with preinstalled dependencies.
- Keep patches small and easy to review.
- Stop after the requested milestone and summarize changes.
