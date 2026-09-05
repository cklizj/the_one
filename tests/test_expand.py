"""Tests for the @file / @- (stdin) value expansion in cli helpers."""
from __future__ import annotations

import pytest

from practice.cli import _expand_value


def test_expand_plain_value_left_alone():
    assert _expand_value("def f(): pass") == "def f(): pass"


def test_expand_none():
    assert _expand_value(None) is None


def test_expand_literal_at_left_alone_when_file_missing(tmp_path):
    assert _expand_value("@todo review") == "@todo review"
    assert _expand_value(f"@{tmp_path / 'missing.cpp'}") == f"@{tmp_path / 'missing.cpp'}"


def test_expand_file_verbatim(tmp_path):
    code = "fn build(n: usize) -> usize {\n\t4 * n\n}\n"
    p = tmp_path / "snippet.rs"
    p.write_text(code)
    assert _expand_value(f"@{p}") == code


def test_expand_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", type("S", (), {"read": lambda self: "class X:\n pass"})())
    assert _expand_value("@-") == "class X:\n pass"