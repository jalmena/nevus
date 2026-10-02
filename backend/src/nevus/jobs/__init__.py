# SPDX-License-Identifier: AGPL-3.0-only
"""Background jobs: a table-backed queue with leases, a registry of kinds and a supervisor.

A job kind has three parts. `load` and `store` run in the main process and may use the database
and the blob store; `compute` is a pure, picklable function that runs in a worker process (OpenCV,
PDF rendering) and only sees what `load` returned. A crash in `compute` never takes the web
process down, and a job whose lease expires is picked up again.
"""
