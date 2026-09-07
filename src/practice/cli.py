"""CLI wiring: argument parsing only. Logic lives in core (pure) and db (storage)."""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import typer

from . import core, db, sync

_EPILOG = """
[yellow]Quick start:[/yellow]

  [green]practice[/green] add "Segment tree" --domain algo --tag leetcode --sub "How do nodes merge?"
  [green]practice[/green] show 2
  [green]practice[/green] list --due
  [green]practice[/green] --domain quant       [bright_black]shortcut: list the quant domain[/bright_black]
  [green]practice[/green] attempt 1 good --reflection "solid"
  [green]practice[/green] tips

[bright_black]Every command is scriptable via flags. Add rich content with --approach
(brain-flow), --related (concepts), --media (image/file paths), --link (URLs).
Your DB lives at <repo>/practice.db and is tracked in git: every run pulls the
latest, and add/edit/attempt are auto-committed and pushed. Override with
--db <path> or $PRACTICE_DB (then it is NOT synced).
Publish to GitHub once (after `gh auth login`): `practice publish`.
Run `practice seed-demo` for a sample DB.

Tab completion for tags/domains (once per shell rc):
  eval "$(_PRACTICE_COMPLETE=zsh_source practice)"     # zsh
  eval "$(_PRACTICE_COMPLETE=bash_source practice)"    # bash[/bright_black]
"""

_EX_ADD = """
[yellow]Example:[/yellow]

  [green]practice[/green] add "Two Sum" -d algo --tag leetcode --tag hashmap \
      --sub "Brute force complexity?" --sub "Why O(n) hash map?" \
      --approach "one pass; key = value, value = index" \
      --related "two-pointer" --media "~/figs/two-sum.png" \
      --link "https://github.com/me/leet/two-sum.py" \
      --notes "variants: sorted array" --code "seen = {}"

[yellow]What each field is for:[/yellow]

  {title}              the prompt you must be able to answer from memory
  --domain  -d         bucket: algo | cpp | quant | system_design | behavioral | general
  --tag     -t         labels to filter/search by [repeatable, tab-completes]
  --sub     -s         ordered sub-parts to answer at review [repeatable]
  --approach -a        your reasoning / brain-flow        [hidden in review]
  --related -r         linked concepts to recall          [repeatable]
  --media   -m         diagram / image / file paths       [repeatable]
  --link    -L         reference URLs (GitHub solution, docs) [repeatable]
  --notes   -n         extra context      [hidden until revealed during review]
  --code    -c         reference code     [hidden until revealed during review]

[bright_black]Reading code/notes from a file or stdin (keeps tabs/spaces/newlines):
  practice add "..." --code @snippet.py
  practice add "..." --code @-   then paste + Ctrl-D / heredoc below

Tip: start minimal (`practice add "P vs NP" -d algo`) and enrich later:
practice edit <id> --sub "..." --approach "..." --related ...[/bright_black]
"""

_EX_SHOW = """
[yellow]Examples:[/yellow]

  [green]practice[/green] show 3                  [bright_black]full card for one item[/bright_black]
  [green]practice[/green] -d quant show           [bright_black]full cards for an entire domain[/bright_black]
  [green]practice[/green] show                     [bright_black]full cards for the last search[/bright_black]
"""

_EX_EDIT = """
[yellow]Examples:[/yellow]

  [green]practice[/green] edit 3 --approach "new brain-flow text"
  [green]practice[/green] edit 3 --related section-tree --related sparse-table
  [green]practice[/green] edit 3 --link https://github.com/me/sol.py --link https://x.dev/ref
  [green]practice[/green] edit 3 --tag cpp --tag memory-layout     [bright_black](replaces tags)[/bright_black]
  [green]practice[/green] edit 3 --clean notes                     [bright_black](clears notes)[/bright_black]
"""

_EX_DELETE = """
[yellow]Examples:[/yellow]

  [green]practice[/green] delete 3                  [bright_black]confirm, then delete item #3[/bright_black]
  [green]practice[/green] delete 3 --force          [bright_black]delete without prompting[/bright_black]
"""

_EX_TIPS = """
[yellow]Example:[/yellow]

  [green]practice[/green] tips
"""

_EX_LIST = """
[yellow]Examples:[/yellow]

  [green]practice[/green] list
  [green]practice[/green] list --due
  [green]practice[/green] list --domain cpp --tag cpp
  [green]practice[/green] --domain cpp[bright_black]   (global shortcut, same as `list --domain cpp`)[/bright_black]
"""

_EX_SEARCH = """
[yellow]Examples:[/yellow]

  [green]practice[/green] search hashmap
  [green]practice[/green] search "segment tree"
  [green]practice[/green] search merge --domain algo --due
  [green]practice[/green] search Two show             [bright_black]list + full cards in one go[/bright_black]
  [green]practice[/green] search Two --show           [bright_black]same, via flag[/bright_black]

[bright_black]Matches title, notes, code, approach (brain-flow), related,
media, subquestions, and tags. Multiple words are ANDed.
Tab-complete --tag, --related, and --domain values.
Run `practice show` (no id) right after to view all results in full.[/bright_black]
"""

_EX_ATTEMPT = """
[yellow]Example:[/yellow]

  [green]practice[/green] attempt 3 good --reflection "merge finally clicked"

[bright_black]Rating delays (anchored to this attempt): again=1d, hard=3d,
good=7d, easy=14d.[/bright_black]
"""

_EX_SEED = """
[yellow]Example:[/yellow]

  export PRACTICE_DB=./demo.db
  [green]practice[/green] seed-demo
  [green]practice[/green] list --due
"""

_EX_TAG_LIST = """
[yellow]Example:[/yellow]

  [green]practice[/green] tag list
"""

_EX_TAG_RENAME = """
[yellow]Example:[/yellow]

  [green]practice[/green] tag rename leetcode algo-leetcode

[bright_black]If the new name already exists, items are merged into it.[/bright_black]
"""

app = typer.Typer(
    name="practice",
    no_args_is_help=True,
    add_completion=False,
    help="Deliberate-practice tracker: multi-domain item + attempts + scheduling.",
    epilog=_EPILOG,
    rich_markup_mode="rich",
)

tag_app = typer.Typer(no_args_is_help=True, help="Tag management.", rich_markup_mode="rich")
app.add_typer(tag_app, name="tag")


def _conn(ctx: typer.Context) -> sqlite3.Connection:
    return ctx.obj["conn"]


KNOWN_DOMAINS = ["algo", "cpp", "quant", "system_design", "behavioral", "general"]


def _completion_db_path(ctx: typer.Context | None) -> Path:
    """DB path for completion callbacks: honor --db (or $PRACTICE_DB / default)."""
    root = ctx.find_root() if ctx is not None else None
    db_param = root.params.get("db") if root is not None else None
    return Path(db_param) if db_param else db.default_db_path()


def _complete_tag(ctx: typer.Context, incomplete: str) -> list[str]:
    try:
        conn = db.connect(_completion_db_path(ctx))
        db.migrate(conn)
        names = db.tag_prefixes(conn, incomplete)
        conn.close()
        return names
    except Exception:
        return []


def _complete_domain(ctx: typer.Context, incomplete: str) -> list[str]:
    return [d for d in KNOWN_DOMAINS if d.startswith(incomplete)]


def _root_domain(ctx: typer.Context) -> str | None:
    """The global --domain/-d filter from the root callback, if any."""
    root = ctx.find_root()
    return root.params.get("domain") if root is not None else None


def _after_write(message: str) -> None:
    """Post-write hook: commit the DB change as a new git commit and push."""
    sync.commit_and_push(f"practice: {message}")


def _expand_value(value: str | None) -> str | None:
    """Resolve an @file / @- (stdin) reference for text fields.

    `practice add ... --code @snippet.py`  uses the file's contents verbatim
    (tabs, spaces, newlines preserved).
    `practice add ... --code @-`            reads from stdin (handy with heredocs).
    A literal value that just happens to start with '@' is left untouched.
    Returns None unchanged (flag not passed).
    """
    if value is None:
        return None
    if value.startswith("@"):
        ref = value[1:]
        if ref == "-":
            return sys.stdin.read()
        p = Path(ref).expanduser()
        if p.exists():
            return p.read_text()
    return value


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    db_path: Optional[Path] = typer.Option(
        None, "--db", help="SQLite DB path (default: <repo>/practice.db, synced via git)"
    ),
    domain: Optional[str] = typer.Option(
        None, "--domain", "-d", help="Global shortcut: `practice --domain <d>` lists that domain.",
        autocompletion=_complete_domain,
    ),
) -> None:
    sync.pull()  # every run starts by syncing from the remote
    conn = db.connect(db_path or db.default_db_path())
    db.migrate(conn)
    ctx.obj = {"conn": conn}

    # `practice --domain quant` (no subcommand) -> list that domain.
    if ctx.invoked_subcommand is None:
        if domain is not None:
            _run_list(ctx, domain=domain, tag=None, due=False)
        else:
            typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command(
    "add",
    help="Add a new practice item.",
    rich_help_panel="Items",
    epilog=_EX_ADD,
)
def add(
    ctx: typer.Context,
    title: Optional[str] = typer.Argument(
        None,
        help="The prompt/question you must be able to answer from memory. "
             "[yellow]Quote multi-word titles[/yellow] in quotes.", show_default=False,
    ),
    domain: str = typer.Option(
        "general", "--domain", "-d",
        help="Bucket: algo | cpp | quant | system_design | behavioral | general.",
        autocompletion=_complete_domain,
    ),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Label to filter/search by (repeatable, tab-completes).", autocompletion=_complete_tag),
    sub: list[str] = typer.Option([], "--sub", "-s", help="Ordered sub-part to answer at review (repeatable)."),
    notes: str = typer.Option("", "--notes", "-n", help="Extra context (hidden until revealed during review)."),
    code: str = typer.Option("", "--code", "-c", help="Reference code (hidden until revealed during review)."),
    approach: str = typer.Option("", "--approach", "-a", help="Your reasoning / brain-flow (hidden during review)."),
    related: list[str] = typer.Option([], "--related", "-r", help="Linked concept to recall (repeatable, tab-completes).", autocompletion=_complete_tag),
    media: list[str] = typer.Option([], "--media", "-m", help="Diagram/image/file path (repeatable)."),
    link: list[str] = typer.Option([], "--link", "-L", help="Reference URL, e.g. your GitHub solution (repeatable)."),
) -> None:
    if title is None:
        typer.echo(ctx.get_help())
        typer.echo("\n[No title given] Start with the prompt you want to master, "
                   "e.g. `practice add \"Zero-copy in Rust\" -d cpp`.")
        raise typer.Exit()
    item_id = db.insert_item(
        _conn(ctx),
        title=title,
        domain=domain,
        tags=tag,
        subquestions=sub,
        notes=_expand_value(notes),
        code=_expand_value(code),
        approach=_expand_value(approach),
        related=related,
        media=media,
        links=link,
    )
    typer.echo(f"Created item #{item_id}: {title} [{domain}]")
    _after_write(f"add item #{item_id}: {title[:60]}")


def _run_list(
    ctx: typer.Context,
    *,
    domain: str | None,
    tag: str | None,
    due: bool,
) -> None:
    items = db.list_items(_conn(ctx), domain=domain, tag=tag, due_only=due)
    if not items:
        typer.echo("No items.")
        raise typer.Exit()
    _render_items(items)


@app.command(
    "list",
    help="List items with optional filters. Shows due status and tags.",
    rich_help_panel="Items",
    epilog=_EX_LIST,
)
def list_items(
    ctx: typer.Context,
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain.", autocompletion=_complete_domain),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag.", autocompletion=_complete_tag),
    due: bool = typer.Option(False, "--due", help="Only show items that are due."),
) -> None:
    _run_list(ctx, domain=domain or _root_domain(ctx), tag=tag, due=due)


@app.command(
    "search",
    help="Keyword search; append `show` to also render the full cards.",
    rich_help_panel="Items",
    epilog=_EX_SEARCH,
)
def search(
    ctx: typer.Context,
    query: str = typer.Argument(help="Search text (space-separated words are ANDed)."),
    extras: Optional[list[str]] = typer.Argument(
        None, help="Optional trailing `show` to render full cards of the results."
    ),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Restrict to a domain.", autocompletion=_complete_domain),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Restrict to a tag.", autocompletion=_complete_tag),
    due: bool = typer.Option(False, "--due", help="Only show items that are due."),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results."),
    show_after: bool = typer.Option(False, "--show", help="Render full cards after the match list."),
) -> None:
    if extras:
        bad = [e for e in extras if e != "show"]
        if bad:
            typer.echo(f"Unexpected extra argument(s): {', '.join(bad)}", err=True)
            raise typer.Exit(code=1)
        show_after = True
    if domain is None:
        domain = _root_domain(ctx)
    items = db.search_items(
        _conn(ctx), query=query, domain=domain, tag=tag, due_only=due, limit=limit
    )
    if not items:
        typer.echo("No matches.")
        raise typer.Exit()
    ids = [str(i["id"]) for i in items]
    db.set_meta(_conn(ctx), "last_search", ",".join(ids))
    typer.echo(f"{len(items)} match(es):")
    typer.echo("")
    _render_items(items)
    if show_after:
        typer.echo("")
        rendered = _show_items_detail(_conn(ctx), [int(x) for x in ids])
        if rendered == 0:
            typer.echo("(no items remained to render)", err=True)


def _render_items(items: list[dict]) -> None:
    headers = ["ID", "Title", "Domain", "Tags", "Status"]
    rows: list[list[str]] = []

    for it in items:
        title = it["title"]
        if len(title) > 48:
            title = title[:45] + "..."
        status = _status(it)
        rows.append(
            [
                str(it["id"]),
                title,
                it["domain"] or "-",
                it["tags"] or "-",
                status,
            ]
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    typer.echo(line)
    typer.echo("  ".join("-" * w for w in widths))
    for row in rows:
        typer.echo("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))


_RATING_LABELS = {"again": "AGAIN", "hard": "HARD", "good": "GOOD", "easy": "EASY"}


def _resolve_code(code: str) -> str:
    """If `code` points at an existing file, return its contents; otherwise return as-is."""
    if "\n" not in code:
        p = Path(code).expanduser()
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return code


def _render_item_detail(item: dict) -> None:
    typer.echo(f"[Item #{item['id']}] {item['title']}")
    typer.echo(f"  domain   : {item['domain'] or '-'}")
    typer.echo(f"  tags     : {item['tags'] or '-'}")
    typer.echo(f"  status   : {_status(item)}")
    typer.echo(
        f"  attempts : {item['attempt_count']}   "
        f"created {item['created_at'][:10]}  updated {item['updated_at'][:10]}"
    )

    subs = item["subquestions_list"]
    typer.echo("\n  Subquestions:")
    if subs:
        for i, s in enumerate(subs, 1):
            typer.echo(f"    {i}. {s}")
    else:
        typer.echo("    (none)")

    if item.get("approach"):
        typer.echo("\n  Approach (brain-flow):")
        for line in item["approach"].splitlines():
            typer.echo(f"    {line}")

    if item.get("notes"):
        typer.echo("\n  Notes:")
        for line in item["notes"].splitlines():
            typer.echo(f"    {line}")

    if item.get("code"):
        typer.echo("\n  Code:")
        code_text = _resolve_code(item["code"])
        for line in code_text.splitlines():
            typer.echo(f"    {line}")

    related = item["related_list"]
    if related:
        typer.echo("\n  Related concepts:")
        for c in related:
            typer.echo(f"    · {c}")

    media = item["media_list"]
    if media:
        typer.echo("\n  Media:")
        for p in media:
            full = Path(p).expanduser()
            exists = " [exists]" if full.exists() else " [MISSING]"
            typer.echo(f"    · {p}{exists}")

    links = item["links_list"]
    if links:
        typer.echo("\n  Links (references):")
        for ln in links:
            typer.echo(f"    · {ln}")

    attempts = item.get("attempts", [])
    if attempts:
        typer.echo("\n  Attempt history:")
        header = f"    {'when':<11} {'rating':<7} {'next':<11} reflection"
        typer.echo(header)
        for a in attempts:
            when = (a["rated_at"] or "")[:10]
            nxt = (a["next_review"] or "-")[:10]
            rating = _RATING_LABELS.get(a["rating"], a["rating"])
            refl = a["reflection"] or ""
            typer.echo(f"    {when:<11} {rating:<7} {nxt:<11} {refl}")
    else:
        typer.echo("\n  Attempt history: (none yet)")


def _show_items_detail(conn: sqlite3.Connection, ids: list[int]) -> int:
    rendered = 0
    for iid in ids:
        item = db.get_item(conn, iid)
        if item is None:
            continue
        if rendered:
            typer.echo("\n" + "-" * 60)
        _render_item_detail(item)
        rendered += 1
    return rendered


@app.command(
    "show",
    help="Show an item's full content. With no id, show all items from the last search.",
    rich_help_panel="Items",
    epilog=_EX_SHOW,
)
def show(
    ctx: typer.Context,
    item_id: Optional[int] = typer.Argument(None, help="Item id. Omit to show the last search results."),
) -> None:
    conn = _conn(ctx)
    if item_id is not None:
        item = db.get_item(conn, item_id)
        if item is None:
            typer.echo(f"No item with id {item_id}.", err=True)
            raise typer.Exit(code=1)
        _render_item_detail(item)
        return

    domain = _root_domain(ctx)
    if domain is not None:
        items = db.list_items(conn, domain=domain)
        if not items:
            typer.echo(f"No items in domain '{domain}'.")
            raise typer.Exit()
        _show_items_detail(conn, [i["id"] for i in items])
        return

    last = db.get_meta(conn, "last_search")
    if not last:
        typer.echo("No previous search. Run `practice search <query>` first, "
                   "or pass an id: `practice show <id>` or a domain: `practice -d <d> show`.", err=True)
        raise typer.Exit(code=1)
    ids = [int(x) for x in last.split(",") if x]
    rendered = _show_items_detail(conn, ids)
    if rendered == 0:
        typer.echo("No items remain from the last search.", err=True)
        raise typer.Exit(code=1)


@app.command(
    "edit",
    help="Update fields of an existing item.",
    rich_help_panel="Items",
    epilog=_EX_EDIT,
)
def edit(
    ctx: typer.Context,
    item_id: int = typer.Argument(help="Item id."),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="New domain.", autocompletion=_complete_domain),
    tags: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="Replace tags (repeatable).", autocompletion=_complete_tag),
    sub: Optional[list[str]] = typer.Option(None, "--sub", "-s", help="Replace subquestions (repeatable)."),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Replace notes (@file / @- accepted)."),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Replace code (@file / @- accepted)."),
    approach: Optional[str] = typer.Option(None, "--approach", "-a", help="Replace approach/brain-flow (@file / @- accepted)."),
    related: Optional[list[str]] = typer.Option(None, "--related", "-r", help="Replace related concepts (repeatable).", autocompletion=_complete_tag),
    media: Optional[list[str]] = typer.Option(None, "--media", "-m", help="Replace media paths (repeatable)."),
    link: Optional[list[str]] = typer.Option(None, "--link", "-L", help="Replace reference URLs (repeatable)."),
    clean: Optional[str] = typer.Option(None, "--clean", help="Clear a single string field: notes|code|approach."),
) -> None:
    cleanable = {"notes", "code", "approach"}
    if clean is not None and clean not in cleanable:
        typer.echo(f"--clean must be one of {sorted(cleanable)}", err=True)
        raise typer.Exit(code=1)
    if clean is None and all(v is None for v in (title, domain, tags, sub, notes, code, approach, related, media, link)):
        typer.echo("Nothing to update: pass at least one field flag.", err=True)
        raise typer.Exit(code=1)

    if not db.update_item(
        _conn(ctx),
        item_id,
        title=title,
        domain=domain,
        tags=tags,
        subquestions=sub,
        notes=_expand_value(notes) if clean is None else None,
        code=_expand_value(code) if clean is None else None,
        approach=_expand_value(approach) if clean is None else None,
        related=related,
        media=media,
        links=link,
    ):
        typer.echo(f"No item with id {item_id}.", err=True)
        raise typer.Exit(code=1)

    if clean is not None:
        if not db.update_item(_conn(ctx), item_id, **{clean: ""}):
            typer.echo(f"No item with id {item_id}.", err=True)
            raise typer.Exit(code=1)
    typer.echo(f"Updated item #{item_id}.")
    _after_write(f"edit item #{item_id}")


@app.command(
    "delete",
    help="Delete an item by id (permanently, including its attempts and tags).",
    rich_help_panel="Items",
    epilog=_EX_DELETE,
)
def delete(
    ctx: typer.Context,
    item_id: int = typer.Argument(help="Item id to delete (see `practice list`)."),
    force: bool = typer.Option(False, "--force", "-f", help="Skip the confirmation prompt."),
) -> None:
    item = db.get_item(_conn(ctx), item_id)
    if item is None:
        typer.echo(f"No item with id {item_id}.", err=True)
        raise typer.Exit(code=1)
    if not force:
        n = item["attempt_count"]
        hint = f" ({n} attempt{'s' if n != 1 else ''})" if n else ""
        typer.echo(f"Delete item #{item_id}: {item['title']}{hint}?")
        if not typer.confirm("Continue?"):
            typer.echo("Aborted.")
            raise typer.Exit()
    db.delete_item(_conn(ctx), item_id)
    typer.echo(f"Deleted item #{item_id}: {item['title']}")
    _after_write(f"delete item #{item_id}: {item['title'][:60]}")


@app.command(
    "tips",
    help="Show workflow tips and shortcuts.",
    rich_help_panel="Extras",
    epilog=_EX_TIPS,
)
def tips() -> None:
    typer.echo("[yellow]working tips[/yellow]:")
    typer.echo("  · Create with rich content: add \"...\" --approach \"brain-flow\" "
               "--related concept --media ~/fig.png --link github.com/me/sol.py")
    typer.echo("  · Inspect an item:  practice show <id>   (see it all, incl. history)")
    typer.echo("  · Inspect a domain: practice -d quant show")
    typer.echo("  · Inspect a search: practice search <words>  ->  practice show  (no id, all cards)")
    typer.echo("  · One-liner:        practice search <words> show")
    typer.echo("  · Fix/append later: practice edit <id> --approach \"...\" --related more")
    typer.echo("  · Add code easily:  practice edit <id> --code @snippet.py   (or @- for stdin)")
    typer.echo("  · Clear a field:    practice edit <id> --clean notes")
    typer.echo("  · Find an item:     practice search <words> --domain cpp --due")
    typer.echo("  · Daily flow:       practice list --due  ->  practice attempt <id> good")
    typer.echo("  · Scriptable: every command works with flags; no interactive prompts")
    typer.echo("  · Tab complete tags/domains with the completion setup in --help")


@app.command(
    "attempt",
    help="Record an attempt non-interactively (for scripting).",
    rich_help_panel="Review",
    epilog=_EX_ATTEMPT,
)
def attempt(
    ctx: typer.Context,
    item_id: int = typer.Argument(help="Item id (see `practice list`)."),
    rating: str = typer.Argument(
        help=f"Rating: one of {', '.join(sorted(core.VALID_RATINGS))}",
    ),
    reflection: str = typer.Option("", "--reflection", "-r", help="Optional reflection text."),
) -> None:
    attempt_id = db.insert_attempt(
        _conn(ctx), item_id=item_id, rating=rating, reflection=reflection
    )
    next_review = core.next_due(db.now_utc(), rating)
    typer.echo(
        f"Logged attempt #{attempt_id} for item #{item_id} [{rating}] "
        f"-> next review {next_review.date().isoformat()}"
    )
    _after_write(f"attempt item #{item_id} [{rating}]")


@tag_app.command("list", help="List all tags with item counts.", rich_help_panel="Tags", epilog=_EX_TAG_LIST)
def _tags(
    ctx: typer.Context,
) -> None:
    tags = db.list_tags(_conn(ctx))
    if not tags:
        typer.echo("No tags yet.")
        raise typer.Exit()
    typer.echo("Tag  Items")
    typer.echo("---  -----")
    for t in tags:
        typer.echo(f"{t['name']}  {t['item_count']}")


@tag_app.command("rename", help="Rename a tag (merges items if the target exists).", rich_help_panel="Tags", epilog=_EX_TAG_RENAME)
def _rename(
    ctx: typer.Context,
    old: str = typer.Argument(help="Current tag name."),
    new: str = typer.Argument(help="New tag name."),
) -> None:
    if not db.rename_tag(_conn(ctx), old, new):
        typer.echo(f"Tag not found: {old}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Renamed tag '{old}' -> '{new}'.")
    _after_write(f"rename tag '{old}' -> '{new}'")


@app.command(
    "seed-demo",
    help="Create a sample DB with realistic items + attempts.",
    epilog=_EX_SEED,
)
def seed_demo(
    ctx: typer.Context,
) -> None:
    """Populate the current DB with demo items and backdated attempts (for trying the CLI)."""
    import datetime as dt

    from .demo_data import DEMO_ATTEMPTS, DEMO_ITEMS

    sqlite = _conn(ctx)
    ids: list[int] = []
    for it in DEMO_ITEMS:
        ids.append(
            db.insert_item(
                sqlite,
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
            sqlite,
            item_id=ids[idx],
            rating=rating,
            reflection=reflection,
            at=db.now_utc() - dt.timedelta(days=days_ago),
        )
    typer.echo(
        f"Seeded {len(DEMO_ITEMS)} items + {len(DEMO_ATTEMPTS)} attempts "
        f"-> {db.default_db_path()}"
    )
    _after_write("seed demo data")


@app.command(
    "publish",
    help="Create the GitHub repo, push everything (needs gh + gh auth login).",
    rich_help_panel="Extras",
)
def publish(
    ctx: typer.Context,
    name: str = typer.Option("practice-tracker", "--name", help="GitHub repository name."),
    private: bool = typer.Option(True, "--private/--public", help="Create a private repo."),
    org: Optional[str] = typer.Option(None, "--org", help="Owner (user or org); default = your account."),
) -> None:
    """One-shot publish: commit local state, then create the GitHub repo and push.

    Requires the GitHub CLI and an authenticated session:
      gh auth login
    Then:  practice publish [--name NAME] [--public]
    """
    del ctx
    if shutil.which("gh") is None:
        typer.echo("GitHub CLI not found. Install it (https://cli.github.com) and run `gh auth login`.", err=True)
        raise typer.Exit(code=1)
    code, _out, err = sync.run_gh("auth", "status")
    if code != 0:
        typer.echo(f"Not authenticated with GitHub CLI:\n  {err}", err=True)
        typer.echo("Run `gh auth login` first, then retry.", err=True)
        raise typer.Exit(code=1)

    sync.commit_and_push("publish: snapshot before GitHub")

    owner = org or _gh_login()
    target = f"{owner}/{name}" if owner else name
    flags = ["--source", str(sync.repo_root()), "--push"]
    flags.append("--private" if private else "--public")
    code, out, err = sync.run_gh("repo", "create", target, *flags)
    if code != 0:
        typer.echo(f"gh repo create failed:\n  {err}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Published: {out or f'https://github.com/{target}'}")


def _gh_login() -> str | None:
    code, out, _err = sync.run_gh("api", "user", "--jq", ".login")
    return out.strip() or None


def _status(item: dict) -> str:
    if item["is_due"]:
        return "DUE"
    if item["next_review_dt"] is None:
        return "NEW"
    n = item["next_review_dt"].astimezone()
    remaining = (n.date() - n.now().date()).days
    if remaining <= 0:
        return f"due today ({n.date().isoformat()})"
    return f"in {remaining}d ({n.date().isoformat()})"


if __name__ == "__main__":
    app()