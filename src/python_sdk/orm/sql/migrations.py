import hashlib
import re
import time
from os import PathLike
from pathlib import Path
from typing import Collection, Optional, Type, Union

from psycopg import Connection, Cursor
from pydantic import PostgresDsn
from rich import print
from rich.panel import Panel

from ...conf import settings
from ...domain import SQLModel, SQLTimeStampedModel
from ...utils import enums, find_subclasses

LOCK_KEY = 84212742

UP_RE = re.compile(r"(?s)--\s*migrate:up\s*(.+?)(?:--\s*migrate:down|$)")
DOWN_RE = re.compile(r"(?s)--\s*migrate:down\s*(.+)$")
MIGRATION_TABLE_SCHEMA = (Path(__file__).parent / "migration_table.sql").read_text(encoding="utf-8")


class ORMOperation(enums.StrEnum):
    MIGRATIONS = "migrations"
    MIGRATE = "migrate"
    STATUS = "status"
    CLEAR = "clear"


class ORMSubcommand(enums.StrEnum):
    CREATE = "create"
    DROP = "drop"
    REVERT = "revert"



def get_all_models() -> Collection[Type[SQLModel]]:
    all_models = find_subclasses(SQLModel)

    exclude = [
        SQLModel,
        SQLTimeStampedModel,

    ]
    return [m for m in all_models if issubclass(m, SQLModel) and m not in exclude]


def parse_migration(path: Path):
    txt = path.read_text(encoding="utf-8")
    up = (UP_RE.search(txt) or [None, ""])[1].strip()
    down = (DOWN_RE.search(txt) or [None, ""])[1].strip()
    no_tx = "-- no-transaction" in txt.splitlines()[0].lower() if txt else False
    ver = path.stem
    chksum = hashlib.sha256(up.encode()).hexdigest()
    return ver, up, down, chksum, no_tx


def list_migrations(migrations_dir: Path) -> list[Path]:
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory {migrations_dir} does not exist.")
    if not migrations_dir.is_dir():
        raise NotADirectoryError(f"{migrations_dir} is not a directory.")
    if not migrations_dir.is_absolute():
        migrations_dir = migrations_dir.resolve()
    return sorted(p for p in migrations_dir.glob("*.sql"))


def ensure_bookkeeping(cur: Cursor):
    cur.execute(MIGRATION_TABLE_SCHEMA)


def get_applied(cur: Cursor) -> dict[str, tuple[str, bool]]:
    cur.execute("SELECT version, checksum, dirty FROM schema_migrations ORDER BY version;")
    return {r[0]: (r[1], r[2]) for r in cur.fetchall()}


def apply_one(conn: Connection, cur: Cursor, path: Path, target_version: str | None = None, fake=False):
    ver, up, _down, chksum, no_tx = parse_migration(path)
    if not up:
        raise ValueError(f"{path.name} missing '-- migrate:up' section")
    t0 = time.perf_counter()
    if fake:
        cur.execute("INSERT INTO schema_migrations(version,name,checksum,execution_ms,dirty) VALUES(%s,%s,%s,%s,false)",
                    (ver, path.name, chksum, 0))
        return

    if no_tx:
        # run outside tx block
        cur.execute("BEGIN; SELECT pg_advisory_xact_lock(%s); COMMIT;", (LOCK_KEY,))
        with conn.cursor() as c2:
            c2.execute("SELECT pg_advisory_lock(%s);", (LOCK_KEY,))
            try:
                c2.execute(up)
                exec_ms = int((time.perf_counter() - t0) * 1000)
                c2.execute(
                    "INSERT INTO schema_migrations(version,name,checksum,execution_ms,dirty) VALUES(%s,%s,%s,%s,false)",
                    (ver, path.name, chksum, exec_ms))
            finally:
                c2.execute("SELECT pg_advisory_unlock(%s);", (LOCK_KEY,))
        return

    cur.execute("BEGIN;")
    try:
        cur.execute("SELECT pg_advisory_xact_lock(%s);", (LOCK_KEY,))
        cur.execute("INSERT INTO schema_migrations(version,name,checksum,execution_ms,dirty) VALUES(%s,%s,%s,%s,true)",
                    (ver, path.name, chksum, 0))
        cur.execute(up)
        exec_ms = int((time.perf_counter() - t0) * 1000)
        cur.execute(
            "UPDATE schema_migrations SET execution_ms=%s, dirty=false WHERE version=%s",
            (exec_ms, ver),
        )
        cur.execute("COMMIT;")
    except Exception:
        cur.execute("ROLLBACK;")
        raise


def rollback_one(cur: Cursor, path: Path, fake=False):
    ver, _up, down, _chksum, no_tx = parse_migration(path)
    if not down:
        raise ValueError(f"{path.name} missing '-- migrate:down' section")
    if fake:
        cur.execute("DELETE FROM schema_migrations WHERE version=%s", (ver,))
        return
    if no_tx:
        cur.execute("SELECT pg_advisory_lock(%s);", (LOCK_KEY,))
        try:
            cur.execute(down)
            cur.execute("DELETE FROM schema_migrations WHERE version=%s", (ver,))
        finally:
            cur.execute("SELECT pg_advisory_unlock(%s);", (LOCK_KEY,))
        return
    cur.execute("BEGIN;")
    try:
        cur.execute("SELECT pg_advisory_xact_lock(%s);", (LOCK_KEY,))
        cur.execute(down)
        cur.execute("DELETE FROM schema_migrations WHERE version=%s", (ver,))
        cur.execute("COMMIT;")
    except Exception:
        cur.execute("ROLLBACK;")
        raise


def print_status(cur: Cursor, files: list[Path], applied: Optional[dict[str, tuple[str, bool]]] = None) -> None:
    """
    Print the status of migrations, showing which are applied and which are pending.
    If a migration has a checksum drift, it will be indicated.
    Args:
        cur (Cursor): The database cursor to execute queries.
        files (list[Path]): List of migration files to check against the database.
        applied (Optional[dict[str, tuple[str, bool]]]): A dictionary of applied migrations with their checksums.
    """

    results = []
    applied = applied or get_applied(cur)
    for p in files:
        ver, _u, _d, chksum, _ = parse_migration(p)
        state = "applied" if ver in applied else "pending"
        drift = " (checksum drift!)" if ver in applied and applied[ver][0] != chksum else ""
        results.append(f"{ver}  {state}{drift}")

    status = "\n".join(results).strip() or "No migrations found."
    print(Panel.fit(
        status,
        title="Migrations Status",
        safe_box=True,
        border_style="blue",
        highlight=True,
        padding=1,
    ))


def main(
        *,
        operation: ORMOperation,
        cmd: ORMSubcommand,
        migration_name: Optional[str] = None,
        db_url: Optional[Union[str, PostgresDsn]] = None,
        migrations_dir: Optional[PathLike] = None,
        dry: Optional[bool] = False,
):
    dir_path: Path = Path(migrations_dir or settings.postgres.migrations_dir_path).resolve()
    dir_path.mkdir(parents=True, exist_ok=True)
    url = PostgresDsn(db_url) if db_url else settings.postgres.dsn
    dry = dry if dry else False
    with Connection.connect(
            conninfo=url.unicode_string(),
            autocommit=True,

    ) as conn:
        cur = conn.cursor()
        ensure_bookkeeping(cur)

        files = list_migrations(migrations_dir=dir_path)
        applied = get_applied(cur)
        not_applied = [p for p in files if p.stem not in applied]
        applied_files = [p for p in files if p.stem in applied]
        if operation == ORMOperation.STATUS:
            print_status(cur=cur, files=files, applied=applied)
            return

        if operation == ORMOperation.MIGRATIONS:
            if cmd == ORMSubcommand.CREATE or not cmd:
                if not migration_name:
                    raise ValueError("Migration name is required for 'create' command.")
                timestamp = int(time.time())
                filename = f"{timestamp:010d}_{migration_name}.sql"
                new_path = dir_path / filename
                if new_path.exists():
                    raise FileExistsError(f"Migration file {new_path} already exists.")
                new_path.write_text("-- migrate:up\n\n-- migrate:down\n", encoding="utf-8")
                print(f"Created migration file: {new_path}")
                return

            elif cmd == ORMSubcommand.DROP:
                if not migration_name:
                    raise ValueError("Migration name is required for 'drop' command.")
                path = dir_path / f"{migration_name}.sql"
                if not path.exists():
                    raise FileNotFoundError(f"Migration file {path} does not exist.")
                path.unlink()
                print(f"Dropped migration file: {path}")
                return
            elif cmd == ORMSubcommand.REVERT:
                if not migration_name:
                    raise ValueError("Migration name is required for 'revert' command.")
                path = dir_path / f"{migration_name}.sql"
                if not path.exists():
                    raise FileNotFoundError(f"Migration file {path} does not exist.")
                rollback_one(cur, path, fake=dry)
                print(f"Reverted migration file: {path}")
                return

        elif operation == ORMOperation.MIGRATE:

            if len(not_applied) == 0:
                print("No migrations to apply.")
                return
            for path in not_applied:
                    apply_one(conn, cur, path)
            print("All migrations applied successfully.")
            return
        elif operation == ORMOperation.STATUS:
            print_status(cur=cur, files=files, applied=applied)
            return
        elif operation == ORMOperation.CLEAR:

            for path in applied_files:
                rollback_one(cur, path, fake=dry)
            cur.execute("DROP TABLE IF EXISTS schema_migrations;")
            print("Cleared all migrations and dropped bookkeeping table.")
            return

        raise ValueError(f"Unknown operation: {operation}")
