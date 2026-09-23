# ADR-0001: Record architecture decisions

- Status: Accepted
- Date: 2026-09-23
- Deciders: engineering (architect), with the Product Owner informed

## Context

neVus is a multi-year, privacy-sensitive project with a single engineering role and a Product Owner who decides product behaviour. The brief asks for important architectural decisions to be documented, and several decisions carry regulatory or licensing weight that must remain traceable long after the conversation that produced them is gone.

## Decision

Architecture decisions are recorded as Markdown files under `docs/adr/`, one decision per file, numbered sequentially (`NNNN-short-title.md`), following the template in [`docs/adr/README.md`](README.md): status, date, deciders, context, decision, consequences. Statuses are Proposed, Accepted, Superseded (with a link to the successor) or Deprecated. A record is never rewritten to say something different; it is superseded by a new record. Product decisions with technical consequences (licence, intended use, data boundaries) are recorded here as well, naming the Product Owner as decider.

## Consequences

- Every non-obvious structural choice has a home and a date, and reviewers can ask "which ADR covers this?".
- Records cost a few minutes each; the index in `README.md` must be kept current.
- Documents such as `ARCHITECTURE.md` describe the current state and link to the records that explain how it came to be.
