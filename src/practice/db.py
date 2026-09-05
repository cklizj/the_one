"""Storage layer: connections, migrations, and repository functions."""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from pathlib import Path

from . import core, sync

DEFAULT_DB_PATH = Path.home() / ".practice" / "practice.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "sql" / "migrations"

_RATING_TO_LABEL = {"again": "AGAIN", "hard": "HARD", "good": "GOOD", "easy": "EASY"}


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def default_db_path() -> Path:
    """The tracked DB lives inside the git repo (syncable from any clone)."""
    env = os.environ.get("PRACTICE_DB")
    return Path(env).expanduser() if env else sync.repo_root() / "practice.db"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending .sql files under sql/migrations, tracked by version."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    row = conn.execute(
        "SELECT MAX(version) AS v FROM schema_migrations"
    ).fetchone()
    current = row["v"] if row and row["v"] is not None else 0
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = int(path.name.split("_", 1)[0])
        if version <= current:
            continue
        conn.executescript(path.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, now_utc().isoformat()),
        )
        conn.commit()


# --------------------------------------------------------------------------- repo


def insert_item(
    conn: sqlite3.Connection,
    *,
    title: str,
    domain: str,
    tags: list[str] | None = None,
    subquestions: list[str] | None = None,
    notes: str = "",
    code: str = "",
    approach: str = "",
    related: list[str] | None = None,
    media: list[str] | None = None,
    links: list[str] | None = None,
) -> int:
    now = now_utc().isoformat()
    cur = conn.execute(
        "INSERT INTO items (title, domain, subquestions, notes, code, approach, related, media, links, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            title,
            domain,
            json.dumps(list(subquestions or []), ensure_ascii=False),
            notes,
            code,
            approach,
            json.dumps(list(related or []), ensure_ascii=False),
            json.dumps(list(media or []), ensure_ascii=False),
            json.dumps(list(links or []), ensure_ascii=False),
            now,
            now,
        ),
    )
    item_id = cur.lastrowid
    for name in _uniq(tags or []):
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = conn.execute(
            "SELECT id FROM tags WHERE name = ?", (name,)
        ).fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
            (item_id, tag_id),
        )
    conn.commit()
    return item_id


_ITEM_SELECT = """
    SELECT i.id, i.title, i.domain, i.subquestions, i.notes, i.code,
           i.approach, i.related, i.media, i.links,
           i.created_at, i.updated_at,
           (SELECT a.next_review FROM attempts a
             WHERE a.item_id = i.id
             ORDER BY a.rated_at DESC, a.id DESC LIMIT 1) AS next_review,
           (SELECT COUNT(*) FROM attempts a WHERE a.item_id = i.id) AS attempt_count,
           COALESCE((SELECT GROUP_CONCAT(t.name, ',')
                      FROM tags t JOIN item_tags it ON it.tag_id = t.id
                      WHERE it.item_id = i.id ORDER BY t.name), '') AS tags
    FROM items i
"""


def _decorate_items(rows: list[sqlite3.Row], now_local: dt.datetime) -> list[dict]:
    items: list[dict] = []
    for r in rows:
        item = dict(r)
        if r["next_review"] is not None:
            item["next_review_dt"] = dt.datetime.fromisoformat(r["next_review"])
        else:
            item["next_review_dt"] = None
        item["is_due"] = core.is_due(item["next_review_dt"], now_local)
        item["subquestions_list"] = json.loads(item["subquestions"] or "[]")
        item["related_list"] = json.loads(item["related"] or "[]")
        item["media_list"] = json.loads(item["media"] or "[]")
        item["links_list"] = json.loads(item["links"] or "[]")
        items.append(item)
    return items


def list_items(
    conn: sqlite3.Connection,
    *,
    domain: str | None = None,
    tag: str | None = None,
    due_only: bool = False,
    now_local: dt.datetime | None = None,
) -> list[dict]:
    now_local = now_local or dt.datetime.now().astimezone()
    sql = _ITEM_SELECT
    where: list[str] = []
    params: list[object] = []
    if domain:
        where.append("i.domain = ?")
        params.append(domain)
    if tag:
        where.append(
            "EXISTS (SELECT 1 FROM item_tags it JOIN tags t ON t.id = it.tag_id "
            "WHERE it.item_id = i.id AND t.name = ?)"
        )
        params.append(tag)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY i.created_at DESC, i.id DESC"

    rows = conn.execute(sql, params).fetchall()
    items = _decorate_items(rows, now_local)
    if due_only:
        items = [i for i in items if i["is_due"]]
    return items


def search_items(
    conn: sqlite3.Connection,
    *,
    query: str,
    domain: str | None = None,
    tag: str | None = None,
    due_only: bool = False,
    limit: int = 50,
    now_local: dt.datetime | None = None,
) -> list[dict]:
    """Full-text-ish search across title, notes, code, subquestions, and tags.

    Multiple space-separated words are ANDed (all must match somewhere).
    """
    now_local = now_local or dt.datetime.now().astimezone()
    words = [w for w in query.split() if w]
    sql = _ITEM_SELECT
    where: list[str] = []
    params: list[object] = []

    tag_shape = (
        "EXISTS (SELECT 1 FROM item_tags it JOIN tags t ON t.id = it.tag_id "
        "WHERE it.item_id = i.id AND t.name = ?)"
    )
    if tag:
        where.append(tag_shape)
        params.append(tag)

    if domain:
        where.append("i.domain = ?")
        params.append(domain)

    if words:
        word_clauses: list[str] = []
        for w in words:
            like = f"%{w}%"
            word_clauses.append(
                "(i.title LIKE ? OR i.notes LIKE ? OR i.code LIKE ? "
                "OR i.approach LIKE ? OR i.related LIKE ? OR i.media LIKE ? "
                f"OR i.links LIKE ? OR i.subquestions LIKE ? OR {tag_shape})"
            )
            params.extend([like, like, like, like, like, like, like, like, w])
        where.append("(" + " AND ".join(word_clauses) + ")")

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY i.updated_at DESC, i.id DESC LIMIT ?"
    params.append(max(1, int(limit)))

    rows = conn.execute(sql, params).fetchall()
    items = _decorate_items(rows, now_local)
    if due_only:
        items = [i for i in items if i["is_due"]]
    return items


def tag_prefixes(conn: sqlite3.Connection, prefix: str = "", limit: int = 50) -> list[str]:
    """Tag names matching a prefix, for shell tab completion."""
    sql = "SELECT name FROM tags WHERE name LIKE ? ORDER BY name LIMIT ?"
    rows = conn.execute(sql, (f"{prefix}%", max(1, int(limit)))).fetchall()
    return [r["name"] for r in rows]


def get_item(
    conn: sqlite3.Connection,
    item_id: int,
    now_local: dt.datetime | None = None,
) -> dict | None:
    """A single item (decorated) plus its attempt history, or None if missing."""
    now_local = now_local or dt.datetime.now().astimezone()
    row = conn.execute(_ITEM_SELECT + " WHERE i.id = ?", (item_id,)).fetchone()
    if row is None:
        return None
    item = _decorate_items([row], now_local)[0]
    item["attempts"] = [
        dict(r)
        for r in conn.execute(
            "SELECT id, item_id, rated_at, rating, next_review, reflection "
            "FROM attempts WHERE item_id = ? ORDER BY rated_at, id",
            (item_id,),
        ).fetchall()
    ]
    return item


def update_item(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    title: str | None = None,
    domain: str | None = None,
    tags: list[str] | None = None,
    subquestions: list[str] | None = None,
    notes: str | None = None,
    code: str | None = None,
    approach: str | None = None,
    related: list[str] | None = None,
    media: list[str] | None = None,
    links: list[str] | None = None,
) -> bool:
    """Update the provided fields of an item. Tags/JSON lists replace the whole list."""
    if conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone() is None:
        return False
    sets: list[str] = []
    params: list[object] = []

    def _set(col: str, value: object) -> None:
        sets.append(f"{col} = ?")
        params.append(value)

    for col, value in (
        ("title", title),
        ("domain", domain),
        ("notes", notes),
        ("code", code),
        ("approach", approach),
    ):
        if value is not None:
            _set(col, value)
    for col, value, is_list in (
        ("subquestions", subquestions, True),
        ("related", related, True),
        ("media", media, True),
        ("links", links, True),
    ):
        if value is not None:
            _set(col, json.dumps(_uniq(value) if is_list else value, ensure_ascii=False))

    if sets:
        sets.append("updated_at = ?")
        params.append(now_utc().isoformat())
        params.append(item_id)
        conn.execute(
            f"UPDATE items SET {', '.join(sets)} WHERE id = ?", params
        )
    if tags is not None:
        conn.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))
        for name in _uniq(tags):
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
            tag_id = conn.execute(
                "SELECT id FROM tags WHERE name = ?", (name,)
            ).fetchone()["id"]
            conn.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
                (item_id, tag_id),
            )
    conn.commit()
    return True


def list_tags(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT t.id, t.name, COUNT(it.item_id) AS item_count "
        "FROM tags t LEFT JOIN item_tags it ON it.tag_id = t.id "
        "GROUP BY t.id, t.name ORDER BY t.name"
    ).fetchall()
    return [dict(r) for r in rows]


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def rename_tag(conn: sqlite3.Connection, old: str, new: str) -> bool:
    old_row = conn.execute("SELECT id FROM tags WHERE name = ?", (old,)).fetchone()
    if old_row is None:
        return False
    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (new,))
    new_row = conn.execute("SELECT id FROM tags WHERE name = ?", (new,)).fetchone()
    if new_row["id"] == old_row["id"]:
        conn.commit()
        return True
    conn.execute(
        "UPDATE OR IGNORE item_tags SET tag_id = ? WHERE tag_id = ?",
        (new_row["id"], old_row["id"]),
    )
    conn.execute("DELETE FROM tags WHERE id = ?", (old_row["id"],))
    conn.commit()
    return True


def insert_attempt(
    conn: sqlite3.Connection,
    *,
    item_id: int,
    rating: str,
    reflection: str = "",
    at: dt.datetime | None = None,
) -> int:
    """Record an attempt and schedule next_review from the latest attempt time."""
    rated_at = at or now_utc()
    next_review = core.next_due(rated_at, rating)
    cur = conn.execute(
        "INSERT INTO attempts (item_id, rated_at, rating, next_review, reflection) "
        "VALUES (?, ?, ?, ?, ?)",
        (item_id, rated_at.isoformat(), rating, next_review.isoformat(), reflection),
    )
    conn.execute("UPDATE items SET updated_at = ? WHERE id = ?", (rated_at.isoformat(), item_id))
    conn.commit()
    return cur.lastrowid


def _uniq(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out