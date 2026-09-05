"""Tests for db-level search and tag lookups (using a temp SQLite file)."""
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
def seeded(conn):
    seg = db.insert_item(
        conn,
        title="Segment tree build / query",
        domain="algo",
        tags=["leetcode", "segment-tree"],
        subquestions=["How do nodes merge?", "What bounds?"],
        notes="build O(n), query O(log n)",
        code="def build(): ...",
    )
    ptr = db.insert_item(
        conn,
        title="Virtual functions & vtable",
        domain="cpp",
        tags=["cpp", "memory"],
        subquestions=["Where is the vptr?"],
        notes="one vptr per object",
    )
    return seg, ptr


def test_search_title(seeded, conn):
    got = db.search_items(conn, query="segment tree")
    assert [i["id"] for i in got] == [seeded[0]]


def test_search_notes(seeded, conn):
    got = db.search_items(conn, query="vptr")
    assert [i["id"] for i in got] == [seeded[1]]


def test_search_subquestions_json(seeded, conn):
    got = db.search_items(conn, query="merge")
    assert [i["id"] for i in got] == [seeded[0]]


def test_search_tag(seeded, conn):
    got = db.search_items(conn, query="segment-tree")
    assert [i["id"] for i in got] == [seeded[0]]


def test_search_code(seeded, conn):
    got = db.search_items(conn, query="def build")
    assert [i["id"] for i in got] == [seeded[0]]


def test_search_multiple_words_anded(seeded, conn):
    assert db.search_items(conn, query="segment hardbound") == []
    assert [i["id"] for i in db.search_items(conn, query="segment merge")] == [seeded[0]]


def test_search_domain_and_tag_filters(seeded, conn):
    got = db.search_items(conn, query="", domain="cpp")
    assert [i["id"] for i in got] == [seeded[1]]
    got = db.search_items(conn, query="", tag="leetcode")
    assert [i["id"] for i in got] == [seeded[0]]


def test_search_limit(seeded, conn):
    got = db.search_items(conn, query="", limit=1)
    assert len(got) == 1


def test_tag_prefixes(seeded, conn):
    assert db.tag_prefixes(conn, "se") == ["segment-tree"]
    assert db.tag_prefixes(conn, "") == sorted(
        ["leetcode", "segment-tree", "cpp", "memory"]
    )


def test_tag_prefixes_empty_db(conn):
    assert db.tag_prefixes(conn, "x") == []