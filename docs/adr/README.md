# Architecture decision records

Decisions that shape neVus, one file each, numbered in the order they were taken. Format and rules are set by [ADR-0001](0001-record-architecture-decisions.md).

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-reimplement-instead-of-fork.md) | Reimplement neVus instead of forking MoleMapper | Accepted |
| [0003](0003-automatic-analysis-boundary.md) | Automatic analysis is opt-in, off by default, experimental and user-confirmed | Accepted |
| [0004](0004-python-fastapi-backend.md) | Python and FastAPI for the backend | Accepted |
| [0005](0005-sqlite-default-postgresql-option.md) | SQLite by default, PostgreSQL as a configurable option | Accepted |
| [0006](0006-content-addressed-image-store.md) | Content-addressed image store with scrubbed immutable originals | Accepted |
| [0007](0007-versioned-analysis-records.md) | Versioned, append-only analysis records | Accepted |
| [0008](0008-react-pwa-frontend.md) | React progressive web application with a token-based design system | Accepted |
| [0009](0009-release-engineering.md) | GitFlow with Conventional Commits, commitizen and automated publishing | Accepted |

## Template

```markdown
# ADR-NNNN: Title

- Status: Proposed | Accepted | Superseded by ADR-MMMM | Deprecated
- Date: YYYY-MM-DD
- Deciders: who took the decision

## Context

What is the situation and which forces are at play.

## Decision

What was decided, in full sentences.

## Consequences

What becomes easier, what becomes harder, what must follow.
```
