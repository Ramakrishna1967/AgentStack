# Copyright 2026 Oxly Contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for LocalStore's offline fallback storage."""

import os
import sqlite3

from oxly.local_store import LocalStore


def test_save_and_retrieve_roundtrip(local_store, mock_span):
    assert local_store.save_span(mock_span) is True
    unsent = local_store.get_unsent_spans()
    assert len(unsent) == 1
    assert unsent[0].name == mock_span.name


def test_connection_closes_even_when_operation_raises(temp_db, mock_spans):
    """A DB error mid-operation must not leak the connection.

    Every LocalStore method used to close its connection with a bare
    `conn.close()` after the query, with no try/finally -- an exception
    from execute()/executemany() would skip the close and leak the
    connection (and its OS-level file handle) on every failure.

    Reproduce a real failure of exactly the kind named in the original bug
    (WAL lock contention): hold an EXCLUSIVE lock from a second connection
    while LocalStore tries to write, forcing a genuine
    "database is locked" OperationalError. Use a short busy-timeout so the
    test doesn't stall on sqlite3's 5s default. Then prove the connection
    was fully released: on Windows, os.remove() fails with PermissionError
    while a sqlite3 connection to the file is still open, so a clean
    remove is a reliable leak detector.
    """
    store = LocalStore(db_path=temp_db)

    def fast_timeout_conn():
        conn = sqlite3.connect(temp_db, timeout=0.1)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    store._get_conn = fast_timeout_conn

    blocker = sqlite3.connect(temp_db)
    blocker.execute("BEGIN EXCLUSIVE")
    try:
        assert store.save_spans(mock_spans) == 0  # lock contention is caught, not raised
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    os.remove(temp_db)  # raises PermissionError on Windows if LocalStore's connection leaked
