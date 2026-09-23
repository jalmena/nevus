# ADR-0009: GitFlow with Conventional Commits, commitizen and automated publishing

- Status: Accepted
- Date: 2026-09-23
- Deciders: Product Owner (process requirements), engineering (tooling)

## Context

The Product Owner requires GitFlow (`main`, `develop`, `feature/*`, `release/*`, `hotfix/*`), Conventional Commits, Semantic Versioning, GitHub Releases, container images traceable to versions, and an automatic update of the personal CasaOS store on release, without publishing unstable releases. Fully automated release tools such as release-please or semantic-release assume trunk-based flows and conflict with release branches. The Product Owner also requires that commits carry no automated co-author attribution; every commit is signed off by its human author.

## Decision

- `feature/*` branches are integrated into `develop` through pull requests with a linear history. A repository ruleset blocks direct pushes, force pushes and deletions on `main` and `develop`. Merges never add tooling-generated trailers, and the committer identity that ends up in the history must be the author's own personal identity; the exact merge mechanism (platform rebase merge with a personal platform email, or maintainer fast-forward) is recorded in `CONTRIBUTING.md` once chosen.
- `release/X.Y.Z` branches are cut from `develop`; `cz bump` (commitizen) derives the version from the commit history, updates the version files (`pyproject.toml`, `package.json`, the compose `x-casaos.version`) and the changelog, in one commit. Release candidates can be built and published as prereleases on demand, never as `latest`.
- The release branch merges into `main` with a merge commit; a workflow on `main` creates the tag `vX.Y.Z` and the GitHub Release from the changelog section; the publish workflow builds multi-architecture images with SBOM and provenance, scans them, smoke-tests them, and opens a pull request in the personal store bumping the image tag, version, date and release notes. `main` is merged back into `develop` by pull request. Hotfixes branch from `main` and follow the same path.
- Commit messages are linted in CI; the Developer Certificate of Origin sign-off is required; no co-author trailers are added by tooling; the web interface's merge buttons are not used.

## Consequences

- One release is one pull request plus one tag; nothing is published from `develop` unless an `edge` tag is deliberately enabled for dogfooding.
- Every artefact (tag, GitHub Release, image, store entry) carries the same version string.
- Required status checks are added to the ruleset as soon as the CI workflows exist.
