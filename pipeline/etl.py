"""
RecipeNLG ETL pipeline.

Usage:
    python etl.py --source recipenlg --file data/recipenlg.jsonl

Requires DATABASE_URL environment variable, e.g.:
    export DATABASE_URL=postgresql://user:pass@localhost:5432/kitchen_portfolio
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from tqdm import tqdm

BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def _content_hash(title: str, ingredients: list[str]) -> str:
    payload = title.strip().lower() + "|" + "|".join(i.strip().lower() for i in ingredients)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_recipenlg(line: str) -> dict | None:
    """Parse one JSONL line from the RecipeNLG dataset."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return None

    title = (raw.get("title") or "").strip()
    if not title:
        return None

    ingredients = raw.get("ingredients") or raw.get("NER") or []
    if isinstance(ingredients, str):
        ingredients = [ingredients]

    directions = raw.get("directions") or raw.get("instructions") or []
    if isinstance(directions, list):
        instructions = "\n".join(str(s) for s in directions)
    else:
        instructions = str(directions)

    source_url = (raw.get("link") or raw.get("source_url") or "").strip() or None

    return {
        "title": title[:512],
        "ingredients": ingredients,
        "instructions": instructions or None,
        "source_url": source_url,
        "content_hash": _content_hash(title, ingredients),
        "raw_json": json.dumps(raw),
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_existing_hashes(cur) -> set[str]:
    cur.execute("SELECT content_hash FROM recipes WHERE content_hash IS NOT NULL")
    return {row[0] for row in cur.fetchall()}


def insert_batch(cur, rows: list[dict], source: str) -> tuple[int, int]:
    """Insert a batch of parsed recipes. Returns (inserted, failed)."""
    inserted = failed = 0
    for row in rows:
        try:
            cur.execute(
                """
                INSERT INTO recipes (source, source_url, title, instructions, content_hash, raw_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    source,
                    row["source_url"],
                    row["title"],
                    row["instructions"],
                    row["content_hash"],
                    row["raw_json"],
                ),
            )

            # Insert raw ingredient texts
            for idx, ing_text in enumerate(row["ingredients"]):
                if not ing_text.strip():
                    continue
                cur.execute(
                    """
                    INSERT INTO recipe_ingredients (recipe_id, raw_text, sort_order)
                    VALUES (
                        (SELECT id FROM recipes WHERE content_hash = %s),
                        %s, %s
                    )
                    """,
                    (row["content_hash"], ing_text.strip()[:255], idx),
                )
            inserted += 1
        except Exception as exc:
            cur.connection.rollback()
            failed += 1
    return inserted, failed


def start_run(cur, source: str, file_path: str) -> int:
    cur.execute(
        """
        INSERT INTO import_runs (source, file_path, status)
        VALUES (%s, %s, 'running') RETURNING id
        """,
        (source, file_path),
    )
    return cur.fetchone()[0]


def finish_run(cur, run_id: int, counts: dict, status: str = "done", error_log: str | None = None):
    cur.execute(
        """
        UPDATE import_runs
        SET finished_at = NOW(),
            records_read      = %s,
            records_inserted  = %s,
            records_skipped   = %s,
            records_failed    = %s,
            error_log         = %s,
            status            = %s
        WHERE id = %s
        """,
        (
            counts["read"],
            counts["inserted"],
            counts["skipped"],
            counts["failed"],
            error_log,
            status,
            run_id,
        ),
    )


# ---------------------------------------------------------------------------
# Main ETL
# ---------------------------------------------------------------------------

def run_etl(source: str, file_path: str):
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("ERROR: DATABASE_URL environment variable is not set.")

    if not os.path.exists(file_path):
        sys.exit(f"ERROR: File not found: {file_path}")

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    run_id = start_run(cur, source, file_path)
    conn.commit()

    existing_hashes = get_existing_hashes(cur)
    print(f"Existing recipes in DB: {len(existing_hashes):,}")

    counts = {"read": 0, "inserted": 0, "skipped": 0, "failed": 0}
    batch: list[dict] = []
    error_messages: list[str] = []

    try:
        with open(file_path, encoding="utf-8") as fh:
            for line in tqdm(fh, desc="Reading", unit=" lines"):
                line = line.strip()
                if not line:
                    continue

                counts["read"] += 1
                parsed = parse_recipenlg(line)

                if parsed is None:
                    counts["failed"] += 1
                    error_messages.append(f"Line {counts['read']}: parse error")
                    continue

                if parsed["content_hash"] in existing_hashes:
                    counts["skipped"] += 1
                    continue

                existing_hashes.add(parsed["content_hash"])
                batch.append(parsed)

                if len(batch) >= BATCH_SIZE:
                    ins, fail = insert_batch(cur, batch, source)
                    conn.commit()
                    counts["inserted"] += ins
                    counts["failed"] += fail
                    batch = []

        # flush remainder
        if batch:
            ins, fail = insert_batch(cur, batch, source)
            conn.commit()
            counts["inserted"] += ins
            counts["failed"] += fail

        finish_run(cur, run_id, counts, status="done",
                   error_log="\n".join(error_messages) or None)
        conn.commit()

    except Exception as exc:
        conn.rollback()
        finish_run(cur, run_id, counts, status="error", error_log=str(exc))
        conn.commit()
        raise
    finally:
        cur.close()
        conn.close()

    print(
        f"\nDone — read: {counts['read']:,} | "
        f"inserted: {counts['inserted']:,} | "
        f"skipped: {counts['skipped']:,} | "
        f"failed: {counts['failed']:,}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Recipe ETL pipeline")
    parser.add_argument("--source", required=True, help="Source name, e.g. recipenlg")
    parser.add_argument("--file", required=True, dest="file_path",
                        help="Path to the JSONL input file")
    args = parser.parse_args()
    run_etl(args.source, args.file_path)


if __name__ == "__main__":
    main()
