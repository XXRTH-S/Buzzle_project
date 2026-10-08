"""Initialize an EMPTY Buzzle project; never overwrite existing tables.

Dry run (default) executes and validates DDL, then rolls back. --apply commits.
Uses the local schema source; intentionally does not claim Supabase CLI migration history.
"""
import argparse
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import psycopg
from psycopg import sql
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("media", "segments", "words", "summaries", "jobs")
SEQUENCES = ("segments_id_seq", "jobs_id_seq")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    uri = dotenv_values(ROOT / ".env").get("DATABASE_URL", "")
    u = urlsplit(uri)
    if not (u.scheme in ("postgres", "postgresql") and u.hostname
            and u.hostname.endswith(".pooler.supabase.com") and u.port == 5432
            and u.username == "postgres.ptklhaxkhluqmcpjyrma"
            and parse_qs(u.query).get("sslmode") == ["require"]):
        raise ValueError("Expected project session pooler with sslmode=require")
    with psycopg.connect(uri, connect_timeout=15, autocommit=True) as c:
        if not c.pgconn.ssl_in_use:
            raise ValueError("TLS is required")
        print("TLS verified", flush=True)
        c.execute("BEGIN")
        try:
            c.execute("SET LOCAL statement_timeout = '30s'")
            c.execute("SET LOCAL lock_timeout = '5s'")
            c.execute("SET LOCAL search_path = public, extensions")
            c.execute("SELECT pg_advisory_xact_lock(742103991)")
            existing = c.execute(
                "SELECT relname FROM pg_class WHERE relnamespace='public'::regnamespace AND relname=ANY(%s)",
                (list(TABLES + SEQUENCES),),
            ).fetchall()
            if existing:
                raise ValueError("Buzzle objects already exist; refusing to overwrite")
            c.execute((ROOT / "app/schema.sql").read_text(encoding="utf-8"))
            for table in TABLES:
                identifier = sql.Identifier("public", table)
                c.execute(sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(identifier))
                c.execute(sql.SQL("REVOKE ALL ON TABLE {} FROM PUBLIC, anon, authenticated").format(identifier))
            for sequence in SEQUENCES:
                c.execute(sql.SQL("REVOKE ALL ON SEQUENCE {} FROM PUBLIC, anon, authenticated").format(sql.Identifier("public", sequence)))
            rows = c.execute(
                "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename=ANY(%s)",
                (list(TABLES),),
            ).fetchall()
            if len(rows) != 5 or not all(row[1] for row in rows):
                raise ValueError("RLS validation failed")
            for role in ("anon", "authenticated"):
                for table in TABLES:
                    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                        allowed = c.execute("SELECT has_table_privilege(%s, %s, %s)", (role, "public." + table, privilege)).fetchone()[0]
                        if allowed:
                            raise ValueError("Unexpected public privilege")
            # Server-role read verifies columns without creating sample records.
            c.execute("SELECT id, summary_template FROM public.media LIMIT 0")
            print("Validated: 5 tables, RLS enabled, client roles denied, server query OK")
            c.execute("COMMIT" if args.apply else "ROLLBACK")
            print("Committed" if args.apply else "Dry run rolled back; no schema persisted")
        except Exception:
            c.execute("ROLLBACK")
            raise


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Database errors may carry connection metadata. Do not print raw messages.
        print("Bootstrap failed:", type(error).__name__, "SQLSTATE:", getattr(error, "sqlstate", None))
        raise SystemExit(1)
