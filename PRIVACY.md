# Privacy

neVus is designed so that the only people who can see a household's skin photographs and notes are the members that household chooses. This document explains what data neVus handles, where it lives, who can see it, and how it is removed. It describes the software; the operator who runs it is responsible for the server and its backups.

## What neVus stores

- Photographs of skin marks and the images derived from them (previews, thumbnails, masks used for measurement).
- The capture date and time and the orientation of each photograph; all other metadata embedded by the camera, including GPS coordinates, device serial numbers and maker notes, is removed before the file is written and never stored.
- Body locations, labels, notes and symptom flags written by the person; measurements and their uncertainties; reminder schedules; appointment dates; generated reports.
- Account data: username, optional email address for notifications, password hash, language and theme preferences, second-factor secret when enabled.
- Optional per-person self-description of skin tone, used only to evaluate image algorithms across skin tones; it is never shown as a health attribute and can be left empty.
- An audit log of actions with identifiers only, and technical logs that never contain personal content.

neVus does not store health conclusions. It does not compute or store risk scores, classifications or diagnoses.

## Where the data lives

Everything is stored on the operator's own server, in one data directory: a database file (or an operator-provided PostgreSQL database) and a tree of image files named by their content hash. Nothing is sent to the project, to any cloud service or to third parties. The software contains no analytics or telemetry.

## Who can see what

- Access requires an account. Registration is closed: the administrator creates accounts.
- Each tracked person has an owner and may be shared with other accounts as manager or viewer. Users see only the persons shared with them.
- Images are only served to authenticated, authorised users; there are no public links.
- Administrators can manage accounts and settings; they see personal data only for the persons shared with them, and the audit log shows identifiers rather than content.

## Sharing outside neVus

The only export intended for clinicians is a PDF report that the person generates and carries or sends themselves. neVus creates no share links. Optional notification channels (email, webhooks, calendar feed, Web Push) are configured by the operator, are off by default, and carry labels and dates, never images or notes. Web Push, when enabled, necessarily passes a small message through the browser vendor's push service; the software says so where it is enabled.

## Retention and deletion

- Deleting a lesion, an observation or an image moves it to a trash for 30 days, after which it is purged together with its files. Anything in the trash can be restored during that period.
- Deleting a person removes all their data immediately after the user re-authenticates; only identifiers remain in the audit log.
- The garbage collector removes image files that no record references any more.
- Backups made before a deletion still contain the deleted data until the backup itself is rotated out; the operator's retention policy applies (default 30 daily and 12 monthly snapshots).

## Export

A person's complete record (images, metadata as JSON, measurements as CSV) can be exported at any time as an encrypted bundle. The bundle can be decrypted with the standard `age` tool and read without neVus.

## Backups

Backups are encrypted with a passphrase before they are written. The operator decides where copies go and for how long they are kept; the documentation recommends keeping the passphrase off the server.

## Children and other household members

An adult may manage a child's profile. The software treats every person's data the same way; it is the household's responsibility to decide who manages whom. Persons can be given their own account later and access can be changed or removed at any time.

## Third parties and open source

neVus is open source under the AGPL-3.0-only licence. It bundles third-party libraries and, in later releases, small image-analysis models, all listed with their licences in `THIRD_PARTY_NOTICES.md` and described in `MODEL_CARD.md`. Models shipped with neVus are trained only on datasets whose licences allow it; no user data ever leaves the server for training or evaluation.

## Changes

Changes to this document travel with the release that changes the behaviour and are called out in the release notes.
