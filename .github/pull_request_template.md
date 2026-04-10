## Summary

<!-- 1–3 bullets describing what this PR changes and *why*. Link the issue it closes. -->

- 
- 

Closes #

## Area

<!-- Check all that apply -->

- [ ] Backend — API / routes
- [ ] Backend — Agent pipeline (classify / extract / validate / route)
- [ ] Backend — Services (email, poller, knowledge, files)
- [ ] Backend — Database / migrations
- [ ] Frontend — Dashboard / orders / reviews / analytics
- [ ] Infrastructure / Docker / CI
- [ ] Documentation

## Changes

<!-- A slightly longer description of what was done. Call out anything non-obvious or risky. -->

## How to test

<!-- Concrete steps a reviewer can run locally. Include sample payloads or fixtures where useful. -->

1. 
2. 
3. 

## Checklist

- [ ] Scope is focused — no unrelated refactors, formatting, or drive-by fixes
- [ ] Type hints / TS types are complete; no `any` or `# type: ignore`
- [ ] `ruff check` and `ruff format --check` pass (backend)
- [ ] `pnpm lint` and `pnpm build` pass (frontend)
- [ ] Tests added or updated for the behavior being changed
- [ ] `uv run pytest` passes locally
- [ ] If schema changed: Alembic migration added via `--autogenerate` and reviewed
- [ ] If routing rules / issue tags changed: CLAUDE.md updated
- [ ] No secrets, credentials, or real vendor data committed

## Screenshots / logs

<!-- For UI changes, include before/after screenshots. For pipeline changes, include a trace or correlation-ID log snippet. -->
