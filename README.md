# practice — Deliberate Practice Tracker (CLI v0)

Personal CLI to track deliberate practice across domains (algorithms, C++/systems,
quant interview prep, system design, behavioral) as first-class **practice items**,
with ordered subquestions, tags, notes/code, attempts, and fixed-interval scheduling.

## Architecture

Three layers, strictly separated:

```
src/practice/
  cli.py     CLI wiring (Typer). Parses flags, hands off, prints. No business logic.
  core.py    PURE logic: interval table, next_due, is_due, latest_next_review. No imports of cli/db.
  db.py      Storage: connect, migrations, repository functions. Time handling lives here.
  __init__.py

sql/migrations/001_init.sql   Canonical schema (applied automatically, versioned)
tests/test_core.py            Pure-function unit tests
```

- `cli.py` -> `db.py` (repo calls) and `core.py` (pure helpers). `core.py` never touches I/O.
- The schema stores UTC ISO timestamps; `is_due` judges everything in local time with
  a 1-day grace window.
- Subquestions are a JSON column on `items` (v0). Tags are normalized
  (`tags` + `item_tags`) so they can be renamed/merged cleanly.
- Attempts are append-only; the latest attempt's `next_review` drives due-ness.

## Decisions (from the design interview)

| Branch | Decision |
|---|---|
| Language / tooling | Python 3.12+, Typer / uv, stdlib `sqlite3`, no ORM |
| Scheduling | Per item (not per subquestion) |
| Subquestions | JSON column on `items`; inline `--sub` at add + later append command |
| Tags | Normalized (`tags` + `item_tags`) |
| Attempts | Append-only; rating is the single 4-level field `again|hard|good|easy` |
| Intervals | again=1d, hard=3d, good=7d, easy=14d, anchored to the last attempt |
| Due logic | UTC storage, local "today" judgement + 1 day grace |
| Scriptability | Every command works via flags; `attempt add` is fully non-interactive |
| JSON round-trip | (later) full snapshot; import into empty DB or `--force` wipe |

## Setup

```sh
uv sync
uv run practice --help
```

DB defaults to `~/.practice/practice.db`; override with `--db <path>` or `$PRACTICE_DB`.

## Usage (current slice)

```sh
# add an item with tags, subquestions, and rich content
uv run practice add "Segment tree build/query" \
  --domain algo --tag leetcode --tag cpp \
  --sub "What state does each node store?" \
  --sub "How do nodes merge?" \
  --approach "think recursively: node = answer for its segment; merge = combine children" \
  --related "fenwick-tree" --related "sparse-table" \
  --media "~/figs/seg-tree.png" \
  --notes "build is O(n), query/update are O(log n)"

# inspect full content + attempt history of one item
uv run practice show 1

# fix/append content later
uv run practice edit 1 --approach "new reasoning" --related range-query
uv run practice edit 1 --clean notes

# list (filterable + due view)
uv run practice list
uv run practice list --domain algo --due
uv run practice list --tag leetcode

# keyword search across title/notes/code/approach/related/media/subquestions/tags
uv run practice search "segment tree" --domain algo --due

# record an attempt (fully scriptable)
uv run practice attempt 1 good --reflection "cold on the merge logic"

# tags
uv run practice tag list
uv run practice tag rename leetcode algo-leetcode

# workflow tips
uv run practice tips

uv run pytest
```

Item content fields: `title`, `domain`, `tags`, `subquestions` (ordered), `notes`,
`code`, `approach` (brain-flow), `related` (concept links), `media` (image/file
paths). Media paths are stored as-is and checked for existence in `show`.

## Next

1. Interactive `review` loop (show title + subquestions, reveal notes/code on keypress, rate).
2. `stats` summary.
3. JSON export/import (full snapshot, empty-DB import or `--force`).
4. Subquestion table split + per-subquestion scheduling if ever needed.