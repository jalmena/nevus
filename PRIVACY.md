# Privacy

neVus is designed so that the only people who can see a household's skin photographs and notes are the members that household chooses. This document explains what data neVus handles, where it lives, who can see it, and how it is removed. It describes the software; the operator who runs it is responsible for the server and its backups.

## What neVus stores

- Photographs of skin marks and the images derived from them (previews, thumbnails, masks used for measurement).
- Photographs taken in full-body sessions, one per region of the body in a fixed order, and the positions of the marks pointed at or confirmed on them. Every region can be skipped, and the two that may show intimate areas say so before the photo is taken. Any part of such a photograph can be blurred afterwards: a blurred copy takes its place and the unblurred photograph is removed at once.
- The capture date and time and the orientation of each photograph; all other metadata embedded by the camera, including GPS coordinates, device serial numbers and maker notes, is removed before the file is written and never stored.
- Body locations, labels, notes and symptom flags written by the person; measurements and their uncertainties; reminder schedules; appointment dates; generated reports.
- Account data: username, optional email address for notifications, password hash, language and theme preferences, and, when the second factor is on, its secret (encrypted with the server's key) and the hashes of the recovery codes.
- Optional per-person self-description of skin tone, used only to evaluate image algorithms across skin tones; it is never shown as a health attribute and can be left empty.
- An audit log of actions with identifiers only, and technical logs that never contain personal content.

neVus does not store health conclusions. It does not compute or store risk scores, classifications or diagnoses.

## Where the data lives

Everything is stored on the operator's own server, in one data directory: a database file (or an operator-provided PostgreSQL database) and a tree of image files named by their content hash. Nothing is sent to the project, to any cloud service or to third parties. The software contains no analytics or telemetry.

## What stays on your phone

To work without a connection, the app keeps some data in the browser of the device you use it on:

- the pages you have opened (lists of persons, marks and visits) and small versions of the photographs, at most 400 of them for at most 30 days, so a known page opens offline;
- visits recorded without a connection, with their photographs, until they have been uploaded.

Full-size photographs, originals and exports are never kept there. Signing out removes all of it from that device. On a shared device, sign out when you are done.

## Who can see what

- Access requires an account. Registration is closed: the administrator creates accounts.
- Each tracked person has an owner and may be shared with other accounts as manager or viewer. Users see only the persons shared with them.
- Images are only served to authenticated, authorised users; there are no public links.
- Administrators can manage accounts and settings; they see personal data only for the persons shared with them, and the audit log shows identifiers rather than content.

## Sharing outside neVus

The only export intended for clinicians is a PDF report that the person generates and carries or sends themselves. neVus creates no share links. A report is kept on the server, where everyone with access to the person can download it, until someone deletes it; purging a mark, a visit or a photo also deletes the reports that show it. The data behind a report travels inside the PDF as an attached file, so the clinician's copy is complete without neVus. Optional notification channels (email, webhooks, calendar feed, Web Push) are off by default and carry labels and dates, never images or notes. Webhooks are set up by an administrator and cover only the persons that administrator owns or manages. A calendar link is made by one user for one person, is stored only as a hash, and stops working when that user loses access to the person. Web Push, when enabled, necessarily passes a small message through the browser vendor's push service; the software says so where it is enabled.

## Retention and deletion

- Deleting a lesion, an observation or an image moves it to a trash for 30 days, after which it is purged together with its files. Anything in the trash can be restored during that period.
- Deleting a full-body session removes the session at once and moves its photographs to the same trash; the marks it added to the registry stay, as the person's own records.
- Blurring part of a session photograph does not use the trash: the unblurred photograph and its derived images are deleted immediately, because keeping them would defeat the purpose. Backups made before still contain it until they rotate out.
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
