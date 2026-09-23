# ADR-0007: Versioned, append-only analysis records

- Status: Accepted
- Date: 2026-09-23
- Deciders: engineering; boundary set by the Product Owner in ADR-0003

## Context

Measurements and other computed results will be produced by algorithms that change over years. Historical observations must never be corrupted by a newer algorithm, yet the person should be able to see what a newer algorithm says about an old photograph. Reports must state how each number was produced. Automatic results are experimental and require the person's confirmation ([ADR-0003](0003-automatic-analysis-boundary.md)).

## Decision

Every algorithm is an analyzer with a name, a semantic version, an optional model hash and a parameter schema. Each run writes an analysis record keyed by target, analyzer name, version, model hash, parameter hash and input hash; identical runs are no-ops, new versions add rows next to old ones, and nothing is overwritten. Measurements reference the analysis that produced them and carry the person's confirmation. The interface shows the current analysis per target and can display "as recorded" or "latest algorithm" values side by side. A command re-runs a chosen analyzer over past observations to add new records. Model files ship inside the image under a manifest (hash, licence, training-data summary, metrics) and are never downloaded at runtime; oversized models go into a separate image variant.

## Consequences

- Reports can state exactly which code and model produced each number.
- Storage of analysis rows grows with algorithm versions; rows are small and prunable by policy, never silently.
- Analyzers must be deterministic for given inputs and parameters, and their inputs must be hashable (image hash plus seeds and settings).
- The experimental gate is enforced at the job scheduler: automatic analyzers do not run for persons without the setting, and their outputs stay pending until decided.
