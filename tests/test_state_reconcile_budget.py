"""Expired browse SQL always rolls back; unrelated SQLite errors remain errors."""

import sqlite3

import pytest

import hermes_state_reconcile as reconcile


@pytest.mark.parametrize("phase", ["begin", "ddl"])
@pytest.mark.parametrize("expired", [False, True])
@pytest.mark.parametrize("error_type", [sqlite3.OperationalError, sqlite3.DatabaseError])
def test_budget_interrupt_including_begin_rolls_back(tmp_path, monkeypatch, phase, expired, error_type):
    from hermes_cli import sqlite_safe_read
    import hermes_state_repair
    import hermes_state_schema

    path = tmp_path / "state.db"
    with sqlite3.connect(path) as seed:
        seed.execute("CREATE TABLE history (text TEXT)")
        seed.execute("INSERT INTO history VALUES ('unchanged')")
    before = path.read_bytes()
    budget = reconcile._Budget(60)
    conn = sqlite3.connect(path, isolation_level=None)

    def interrupt():
        budget.expired = expired
        raise error_type("interrupted")

    class Connection:
        def __getattr__(self, name):
            return getattr(conn, name)

        def execute(self, sql, *args):
            if phase == "begin" and sql == "BEGIN IMMEDIATE":
                interrupt()
            return conn.execute(sql, *args)

    def interrupted_ddl(cursor):
        cursor.execute("CREATE TABLE partial_upgrade (id INTEGER)")
        cursor.execute("INSERT INTO history VALUES ('must roll back')")
        interrupt()

    monkeypatch.setattr(sqlite_safe_read, "connect_tracked", lambda *a, **kw: Connection())
    monkeypatch.setattr(hermes_state_repair, "_reapply_durability_barriers", lambda c: None)
    monkeypatch.setattr(hermes_state_schema, "apply_declared_schema", interrupted_ddl)
    expected = reconcile.BrowseBudgetExceeded if expired else error_type
    with pytest.raises(expected) as caught:
        reconcile._apply_additive_schema(path, budget)
    if expired:
        assert isinstance(caught.value.__cause__, error_type)
    else:
        # Negative control: SQLite failures without a fired deadline are not timeouts.
        assert type(caught.value) is error_type
    assert path.read_bytes() == before
    with sqlite3.connect(path) as check:
        assert check.execute("SELECT text FROM history").fetchall() == [("unchanged",)]
        assert check.execute("SELECT name FROM sqlite_master WHERE name='partial_upgrade'").fetchall() == []
