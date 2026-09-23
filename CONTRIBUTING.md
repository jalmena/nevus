# Contributing to neVus

Thank you for considering a contribution. neVus handles some of the most personal data a person has, so the process is a little stricter than average. Everything below is short on purpose.

## Language

All project artefacts are written in English: code, identifiers, comments, documentation, commit messages, branch names, pull requests, issue templates, workflows, test descriptions, error messages, UI text and accessibility labels. Do not mix languages inside a file. Report templates may exist in other languages when the product requires it; that is the only exception.

## Branching (GitFlow)

- `main` always represents production-ready code. Nobody commits to it directly.
- `develop` is the current integration state.
- Work happens on `feature/<short-name>` branches cut from `develop` and merged back through a pull request.
- Releases are prepared on `release/<version>` branches and merged into `main`, then back into `develop`.
- Production fixes use `hotfix/<short-name>` branches cut from `main`.

Pull requests into `main` and `develop` require passing checks. Keep them focused: one logical change per pull request. Merges are performed by a maintainer as a local fast-forward after the checks pass (the web merge buttons are not used), so every commit keeps exactly the identity and sign-off its author gave it.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add lesion timeline
fix: correct body map coordinate calculation
refactor: isolate image processing service
test: add lesion matching integration tests
docs: update CasaOS deployment guide
chore: update dependencies
```

Types in use: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `style`. Add a scope when it helps (`feat(bodymap): …`). A breaking change carries `!` after the type or a `BREAKING CHANGE:` footer.

Every commit carries a Developer Certificate of Origin sign-off (`git commit -s`), which adds `Signed-off-by: Name <email>` and certifies that you have the right to submit the change under the project licence. There is no contributor licence agreement.

## Versioning and releases

Semantic Versioning (`MAJOR.MINOR.PATCH`), Git tags `vX.Y.Z`, GitHub Releases with notes generated from the commit history, container images tagged with the same version. Until 1.0.0 minor versions may contain breaking changes; the release notes say so explicitly.

## Code, tests and documentation

- Every significant change comes with tests at the appropriate level (unit, integration, end-to-end, migration, backup/restore, evaluation for anything statistical).
- Documentation changes travel in the same pull request as the behaviour they describe.
- Architecture decisions are recorded under `docs/adr/`; see [ADR-0001](docs/adr/0001-record-architecture-decisions.md).
- User-facing text stays descriptive. A lint rejects disease names, risk words and diagnostic thresholds in UI copy and report templates; see [ADR-0003](docs/adr/0003-automatic-analysis-boundary.md).

Tooling and conventions per language are described in `DEVELOPMENT.md` once the code base exists.

## Privacy in contributions

- Never attach photographs of real people, real skin or real medical documents to issues, pull requests or test fixtures. Use the synthetic fixtures provided by the project or create synthetic ones.
- Never paste logs that contain personal data. Redact before posting.
- Security problems are reported privately as described in `SECURITY.md` (to be published with the first release candidate), not in public issues.

## Licence of contributions

By contributing you agree that your contribution is licensed under the project licence, the GNU Affero General Public License v3.0 only, and you certify the Developer Certificate of Origin through your sign-off.
