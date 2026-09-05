"""Seed a demo database with practice items across domains and backdated attempts.

Usage:  uv run python scripts/seed_demo.py [--db PATH]   (default: ./demo.db)
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from practice import db
from practice.demo_data import DEMO_ATTEMPTS, DEMO_ITEMS


def seed(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = db.connect(db_path)
    db.migrate(conn)

    item_ids: list[int] = []
    for it in DEMO_ITEMS:
        item_ids.append(
            db.insert_item(
                conn,
                title=it["title"],
                domain=it["domain"],
                tags=it["tags"],
                subquestions=it["subquestions"],
                notes=it["notes"],
                code=it["code"],
                approach=it.get("approach", ""),
                related=it.get("related", []),
                media=it.get("media", []),
                links=it.get("link", []),
            )
        )

    for idx, rating, days_ago, reflection in DEMO_ATTEMPTS:
        db.insert_attempt(
            conn,
            item_id=item_ids[idx],
            rating=rating,
            reflection=reflection,
            at=db.now_utc() - dt.timedelta(days=days_ago),
        )

    conn.close()
    print(f"Seeded {len(DEMO_ITEMS)} items + {len(DEMO_ATTEMPTS)} attempts -> {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="demo.db", help="demo DB path")
    args = parser.parse_args()
    seed(Path(args.db))


if __name__ == "__main__":
    main()