"""MySQL-backed model helpers for website aliases."""

from typing import Any

from app.services.database import _ensure_column, _fetch_rows, ensure_database_ready

DEFAULT_WEBSITE_ENTRIES: list[dict[str, str]] = [
    {
        "alias": "youtube",
        "name": "YouTube",
        "url": "https://www.youtube.com",
        "search_url_template": "https://www.youtube.com/results?search_query={query}",
    },
    {
        "alias": "gmail",
        "name": "Gmail",
        "url": "https://mail.google.com",
        "search_url_template": "",
    },
    {
        "alias": "google",
        "name": "Google",
        "url": "https://www.google.com",
        "search_url_template": "https://www.google.com/search?q={query}",
    },
    {
        "alias": "facebook",
        "name": "Facebook",
        "url": "https://www.facebook.com",
        "search_url_template": "",
    },
    {
        "alias": "github",
        "name": "GitHub",
        "url": "https://github.com",
        "search_url_template": "https://github.com/search?q={query}",
    },
    {
        "alias": "wikipedia",
        "name": "Wikipedia",
        "url": "https://www.wikipedia.org",
        "search_url_template": "https://en.wikipedia.org/w/index.php?search={query}",
    },
]

WEBSITE_ALIASES: dict[str, str] = {
    entry["alias"]: entry["url"] for entry in DEFAULT_WEBSITE_ENTRIES
}


def load_website_aliases() -> dict[str, dict[str, str]]:
    """Load enabled website aliases from MySQL."""
    ensure_database_ready()
    rows = _fetch_rows(
        """
        SELECT alias, display_name, url, search_url_template
        FROM website_aliases
        WHERE enabled = 1
        """
    )
    aliases: dict[str, dict[str, str]] = {}
    for row in rows:
        alias = str(row.get("alias", "")).strip().lower()
        url = str(row.get("url") or "").strip()
        if not alias or not url:
            continue

        aliases[alias] = {
            "name": str(row.get("display_name", alias)).strip() or alias.title(),
            "url": url,
            "search_url_template": str(row.get("search_url_template") or "").strip(),
        }
    return aliases


def ensure_website_alias_schema(connection: Any) -> None:
    """Add newer optional columns to the website_aliases table when needed."""
    _ensure_column(
        connection,
        table_name="website_aliases",
        column_name="search_url_template",
        definition="TEXT NULL",
    )


def seed_default_website_aliases(connection: Any) -> None:
    """Insert missing website aliases and backfill default search templates."""
    cursor = connection.cursor()
    for entry in DEFAULT_WEBSITE_ENTRIES:
        cursor.execute(
            """
            INSERT IGNORE INTO website_aliases (alias, display_name, url, search_url_template, enabled)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                str(entry.get("alias", "")).lower(),
                str(entry.get("name", "")),
                str(entry.get("url", "")),
                str(entry.get("search_url_template", "")),
                True,
            ),
        )
        search_url_template = str(entry.get("search_url_template", "")).strip()
        if search_url_template:
            cursor.execute(
                """
                UPDATE website_aliases
                SET search_url_template = %s
                WHERE alias = %s AND (search_url_template IS NULL OR search_url_template = '')
                """,
                (search_url_template, str(entry.get("alias", "")).lower()),
            )
