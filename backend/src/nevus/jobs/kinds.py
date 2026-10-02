# SPDX-License-Identifier: AGPL-3.0-only
"""Every module that defines job kinds, imported once so the registry is complete in every process."""

import nevus.cv.pipeline
import nevus.maintenance
import nevus.notify.email
import nevus.notify.webhooks
import nevus.reports.jobs
import nevus.sessions.jobs  # noqa: F401
