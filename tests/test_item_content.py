"""Tests for item content fields, get_item, and update_item."""
from __future__ import annotations

import datetime as dt

import pytest

from practice import db

UTC = dt.timezone.utc


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    db.migrate(c)
    yield c
    c.close()


@pytest.fixture()
def item_id(conn):
    return db.insert_item(
        conn,
        title="Segment tree",
        domain="algo",
        tags=["leetcode", "segment-tree"],
        subquestions=["What state does each node store?"],
        notes="build O(n)",
        code="t=[0]*(4*n); build(a)",
        approach="think recursively: merge = combine children",
        related=["fenwick-tree", "sparse-table"],
        media=["~/figs/seg.png", "https://x/y.png"],
    )


def test_insert_and_get_item_fields(item_id, conn):
    item = db.get_item(conn, item_id)
    assert item is not None
    assert item["approach"] == "think recursively: merge = combine children"
    assert item["related_list"] == ["fenwick-tree", "sparse-table"]
    assert item["media_list"] == ["~/figs/seg.png", "https://x/y.png"]
    assert item["subquestions_list"] == ["What state does each node store?"]


def test_get_item_does_not_exist(conn):
    assert db.get_item(conn, 999) is None


def test_get_item_includes_attempts(item_id, conn):
    db.insert_attempt(conn, item_id=item_id, rating="good", reflection="clear now")
    item = db.get_item(conn, item_id)
    assert len(item["attempts"]) == 1
    assert item["attempts"][0]["rating"] == "good"
    assert item["attempts"][0]["reflection"] == "clear now"


def test_update_item_scalar_and_lists(item_id, conn):
    ok = db.update_item(
        conn, item_id, approach="updated flow", related=["fenwick-tree"], media=["~/new.png"]
    )
    assert ok is True
    item = db.get_item(conn, item_id)
    assert item["approach"] == "updated flow"
    assert item["related_list"] == ["fenwick-tree"]
    assert item["media_list"] == ["~/new.png"]
    assert item["title"] == "Segment tree"  # untouched


def test_update_item_tags_replace(item_id, conn):
    db.update_item(conn, item_id, tags=["cpp", "memory"])
    item = db.get_item(conn, item_id)
    assert item["tags"] == "cpp,memory"


def test_update_item_clears_string_field(item_id, conn):
    db.update_item(conn, item_id, notes="")
    item = db.get_item(conn, item_id)
    assert item["notes"] == ""


def test_update_item_missing_item(conn):
    assert db.update_item(conn, 999, title="x") is False


def test_search_matches_approach_and_related(item_id, conn):
    assert [i["id"] for i in db.search_items(conn, query="recursively")] == [item_id]
    assert [i["id"] for i in db.search_items(conn, query="sparse-table")] == [item_id]
    assert [i["id"] for i in db.search_items(conn, query="figs/seg.png")] == [item_id]


def test_links_field_insert_get_and_search(conn):
    iid = db.insert_item(
        conn,
        title="Prefix sums",
        domain="algo",
        links=["https://github.com/me/prefix.py", "https://cp-algorithms.com/pref.html"],
    )
    item = db.get_item(conn, iid)
    assert item["links_list"] == [
        "https://github.com/me/prefix.py",
        "https://cp-algorithms.com/pref.html",
    ]
    assert [i["id"] for i in db.search_items(conn, query="cp-algorithms")] == [iid]


def test_links_default_empty(conn):
    iid = db.insert_item(conn, title="bare", domain="general")
    assert db.get_item(conn, iid)["links_list"] == []


def test_update_links_replace(item_id, conn):
    db.update_item(conn, item_id, links=["https://new.dev/1"])
    assert db.get_item(conn, item_id)["links_list"] == ["https://new.dev/1"]


def test_list_items_includes_new_fields_defaults(conn):
    iid = db.insert_item(conn, title="bare", domain="general")
    item = db.get_item(conn, iid)
    assert item["approach"] == ""
    assert item["related_list"] == []
    assert item["media_list"] == []