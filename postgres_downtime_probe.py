"""Continuous Postgres probe to measure downtime during maintenance events."""

from __future__ import annotations

import argparse
import csv
import os
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError as exc:  # pragma: no cover - dependency guard
    print("Python 3.9+ is required for zoneinfo support.", file=sys.stderr)
    raise

try:
    import psycopg
    from psycopg import sql
except ImportError as exc:  # pragma: no cover - dependency guard
    print(
        "psycopg is required. Install with: pip install 'psycopg[binary]'",
        file=sys.stderr,
    )
    raise


DEFAULT_INTERVAL_SECONDS = 0.1
DEFAULT_TABLE_NAME = "downtime_probe"
DEFAULT_LOG_FILE = "postgres_downtime_probe.log"
LOCAL_TZ = ZoneInfo("America/New_York")


@dataclass
class ProbeStats:
    total_attempts: int = 0
    success_count: int = 0
    failure_count: int = 0


@dataclass
class DowntimeTracker:
    intervals: List[Tuple[datetime, datetime]]
    _current_start: Optional[datetime]

    def __init__(self) -> None:
        self.intervals = []
        self._current_start = None

    def record(self, event_time: datetime, success: bool) -> None:
        if success:
            if self._current_start is not None:
                self.intervals.append((self._current_start, event_time))
                self._current_start = None
        else:
            if self._current_start is None:
                self._current_start = event_time

    def finalize(self, final_time: datetime) -> None:
        if self._current_start is not None:
            self.intervals.append((self._current_start, final_time))
            self._current_start = None


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Continuously inserts timestamps into Postgres to measure downtime "
            "during upgrades. Logs each attempt to a CSV file and reports any "
            "downtime intervals on exit."
        )
    )
    parser.add_argument(
        "--dsn",
        help=(
            "Libpq-formatted connection string. Overrides individual connection "
            "flags when provided."
        ),
    )
    parser.add_argument("--host", default="localhost", help="Postgres host name")
    parser.add_argument("--port", type=int, default=5432, help="Postgres port")
    parser.add_argument("--user", default=os.getenv("PGUSER", "postgres"), help="Postgres user")
    parser.add_argument(
        "--password-env",
        default="PGPASSWORD",
        help="Environment variable to read the password from (default: PGPASSWORD)",
    )
    parser.add_argument(
        "--dbname",
        default=os.getenv("PGDATABASE", "postgres"),
        help="Database name to connect to",
    )
    parser.add_argument(
        "--table-name",
        default=DEFAULT_TABLE_NAME,
        help="Destination table for inserts. Use schema.table for non-default schema.",
    )
    parser.add_argument(
        "--probe-label",
        default=os.getenv("PROBE_LABEL", "upgrade-probe"),
        help="Text label stored with each successful insert",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Delay between attempts in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--log-file",
        default=DEFAULT_LOG_FILE,
        help="Path to the CSV log file for attempt results",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        help="Optional cap on the number of attempts before exiting",
    )
    parser.add_argument(
        "--create-table-only",
        action="store_true",
        help="Bootstrap the table and exit without probing",
    )

    args = parser.parse_args(argv)

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    return args


def split_table_identifier(name: str) -> Tuple[str, ...]:
    parts = tuple(part.strip() for part in name.split("."))
    if not all(parts):
        raise ValueError("Invalid table name; empty identifiers are not allowed")
    if len(parts) not in (1, 2):
        raise ValueError("Table name must be in the form 'table' or 'schema.table'")
    return parts


def resolve_password(var_name: str) -> Optional[str]:
    value = os.getenv(var_name)
    if value:
        return value
    return None


def open_connection(args: argparse.Namespace) -> psycopg.Connection:
    if args.dsn:
        return psycopg.connect(args.dsn, autocommit=True)

    password = resolve_password(args.password_env)
    conn_args = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "dbname": args.dbname,
        "autocommit": True,
    }
    if password is not None:
        conn_args["password"] = password

    return psycopg.connect(**conn_args)


def ensure_table(conn: psycopg.Connection, identifier: Tuple[str, ...]) -> None:
    column_definitions = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {table} (
            id BIGSERIAL PRIMARY KEY,
            observed_at TIMESTAMPTZ NOT NULL,
            probe_label TEXT NOT NULL,
            note TEXT
        )
        """
    )
    with conn.cursor() as cur:
        cur.execute(column_definitions.format(table=sql.Identifier(*identifier)))


def truncate_table(conn: psycopg.Connection, identifier: Tuple[str, ...]) -> None:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {table}").format(table=sql.Identifier(*identifier)))


def build_insert(identifier: Tuple[str, ...]) -> sql.Composed:
    return sql.SQL(
        """
        INSERT INTO {table} (observed_at, probe_label, note)
        VALUES (%s, %s, %s)
        """
    ).format(table=sql.Identifier(*identifier))


def setup_signal_handler(stop_flag: dict) -> None:
    def handler(signum: int, _frame) -> None:  # pragma: no cover - signal handling
        stop_flag["stop"] = True

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def init_log_writer(path: Path) -> Tuple[csv.writer, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists() and path.stat().st_size > 0
    log_file = path.open("a", newline="", encoding="utf-8")
    writer = csv.writer(log_file)
    if not file_exists:
        writer.writerow(["timestamp", "status", "error", "attempt_duration_ms"])
        log_file.flush()
    return writer, log_file


def log_result(
    writer: csv.writer,
    log_file,
    event_time: datetime,
    success: bool,
    error: Optional[str],
    duration_seconds: float,
) -> None:
    writer.writerow(
        [
            event_time.isoformat(),
            "success" if success else "failure",
            error or "",
            f"{duration_seconds * 1000:.3f}",
        ]
    )
    log_file.flush()


def probe_loop(args: argparse.Namespace) -> None:
    stop_flag = {"stop": False}
    setup_signal_handler(stop_flag)

    table_identifier = split_table_identifier(args.table_name)
    log_path = Path(args.log_file).expanduser().resolve()
    writer, log_file = init_log_writer(log_path)

    stats = ProbeStats()
    downtime_tracker = DowntimeTracker()

    insert_stmt = None
    conn: Optional[psycopg.Connection] = None
    bootstrap_attempted = False

    try:
        while not stop_flag["stop"]:
            iteration_start = time.monotonic()
            attempt_time = datetime.now(LOCAL_TZ)
            if args.max_attempts and stats.total_attempts >= args.max_attempts:
                break

            success = False
            error_message = None

            try:
                if conn is None:
                    conn = open_connection(args)
                    insert_stmt = build_insert(table_identifier)
                if not bootstrap_attempted:
                    ensure_table(conn, table_identifier)
                    bootstrap_attempted = True

                with conn.cursor() as cur:
                    cur.execute(insert_stmt, (attempt_time, args.probe_label, None))

                success = True
                stats.success_count += 1
            except Exception as exc:  # broad to include connection errors
                error_message = str(exc)
                stats.failure_count += 1
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:  # pragma: no cover - defensive cleanup
                        pass
                    conn = None
                    insert_stmt = None

            stats.total_attempts += 1
            downtime_tracker.record(attempt_time, success)

            duration = time.monotonic() - iteration_start
            log_result(writer, log_file, attempt_time, success, error_message, duration)

            # Failure details are captured in the log file; avoid spamming stderr to
            # make long-running output easier to read during maintenance windows.

            sleep_time = args.interval - duration
            if sleep_time > 0:
                time.sleep(sleep_time)

    finally:
        end_time = datetime.now(LOCAL_TZ)
        downtime_tracker.finalize(end_time)
        if conn is not None:
            try:
                truncate_table(conn, table_identifier)
            except Exception:
                pass
        log_file.close()
        if conn is not None:
            conn.close()

    summarize(stats, downtime_tracker)


def summarize(stats: ProbeStats, tracker: DowntimeTracker) -> None:
    print("\n=== Probe Summary ===")
    print(f"Total attempts: {stats.total_attempts}")
    print(f"Succeeded: {stats.success_count}")
    print(f"Failed: {stats.failure_count}")

    if tracker.intervals:
        print("\nDowntime intervals detected (America/New_York):")
        for start, end in tracker.intervals:
            duration = end - start
            print(
                f"  - from {start.isoformat()} to {end.isoformat()} "
                f"({duration.total_seconds():.3f} seconds)"
            )
    else:
        print("\nNo downtime intervals detected during probe run.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    table_identifier = split_table_identifier(args.table_name)

    try:
        conn = open_connection(args)
    except Exception as exc:
        print(f"Failed to establish initial connection: {exc}", file=sys.stderr)
        return 2

    try:
        ensure_table(conn, table_identifier)
        truncate_table(conn, table_identifier)
        print(
            f"Table '{args.table_name}' is ready.\n"
            f"Using probe label '{args.probe_label}' and logging to '{args.log_file}'."
        )
    finally:
        conn.close()

    if args.create_table_only:
        return 0

    probe_loop(args)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())


