#!/usr/bin/env python3
"""Generate the almapeople.org landing page.

Scans the people home base for users with a public_html directory and writes
a static HTML index listing them, each linked to their per-user subdomain.
Intended to run from cron as the apache user.
"""

from __future__ import annotations

import argparse
import datetime
import html
import logging
import pwd
import sys
from pathlib import Path

log = logging.getLogger(__name__)

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AlmaPeople</title>
    <style>
        :root {{ --brand: #0c5499; --muted: #555; --border: #e4e4e4; }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            color: #222;
            background: #fafafa;
        }}
        header {{
            background: #082336;
            color: white;
            padding: 2rem 1rem;
            text-align: center;
        }}
        header h1 {{ margin: 0; font-size: 2.4rem; }}
        header p {{ margin: 0.5rem 0 0; opacity: 0.9; }}
        header .logo {{ height: 64px; width: auto; margin-bottom: 0.75rem; }}
        header a {{ color: #9fc3ff; text-decoration: underline; }}
        header a:hover {{ color: white; }}
        main {{ max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }}
        .search {{
            width: 100%;
            padding: 0.6rem 0.8rem;
            font-size: 1rem;
            border: 1px solid var(--border);
            border-radius: 4px;
            margin-bottom: 1rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border: 1px solid var(--border);
            border-radius: 4px;
            overflow: hidden;
        }}
        th, td {{
            text-align: left;
            padding: 0.7rem 1rem;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: #f3f3f3; font-weight: 600; }}
        tbody tr:last-child td {{ border-bottom: none; }}
        tbody tr:hover {{ background: #f8f8f8; }}
        a {{ color: var(--brand); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .count {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem; }}
        footer {{
            text-align: center;
            color: var(--muted);
            font-size: 0.85rem;
            padding: 2rem 1rem;
        }}
    </style>
</head>
<body>
    <header>
        <img class="logo" src="/static/almalinux-logo.svg" alt="AlmaLinux">
        <p>Web space for AlmaLinux contributors.
            <a href="https://wiki.almalinux.org/sigs/infrastructure/almapeople.html">How to use almapeople.org</a>
        </p>
    </header>
    <main>
        <input type="search" id="filter" class="search"
               placeholder="Search by username or name..." autofocus>
        <div class="count"><span id="visible">{count}</span> of {count} users</div>
        <table>
            <thead>
                <tr><th>Username</th><th>Name</th></tr>
            </thead>
            <tbody id="users">
{rows}
            </tbody>
        </table>
    </main>
    <footer>
        Generated {generated}.
    </footer>
    <script>
        (function() {{
            var input = document.getElementById('filter');
            var rows = document.querySelectorAll('#users tr');
            var visible = document.getElementById('visible');
            input.addEventListener('input', function() {{
                var q = input.value.trim().toLowerCase();
                var shown = 0;
                rows.forEach(function(r) {{
                    var match = !q || r.textContent.toLowerCase().indexOf(q) !== -1;
                    r.style.display = match ? '' : 'none';
                    if (match) shown++;
                }});
                visible.textContent = shown;
            }});
        }})();
    </script>
</body>
</html>
"""

ROW_TEMPLATE = (
    '                <tr>'
    '<td><a href="https://{user}.{domain}/">{user}</a></td>'
    '<td>{name}</td>'
    '</tr>'
)


def collect_users(home_base: Path) -> list[tuple[str, str]]:
    """Return sorted (username, gecos) tuples for users with public_html."""
    users: list[tuple[str, str]] = []
    for entry in sorted(home_base.iterdir()):
        if not entry.is_dir():
            continue
        username = entry.name
        try:
            owner = entry.owner()
        except KeyError:
            log.warning("Skipping %s: no named owner", entry)
            continue
        if owner != username:
            log.warning("Skipping %s: owned by %s, not %s", entry, owner, username)
            continue
        try:
            if not (entry / "public_html").is_dir():
                continue
        except PermissionError:
            continue
        try:
            gecos = pwd.getpwnam(username).pw_gecos.split(",")[0]
        except KeyError:
            log.warning("Skipping %s: not in passwd", username)
            continue
        users.append((username, gecos or username))
    return users


def render(users: list[tuple[str, str]], domain: str) -> str:
    rows = "\n".join(
        ROW_TEMPLATE.format(
            user=html.escape(u),
            name=html.escape(name),
            domain=html.escape(domain),
        )
        for u, name in users
    )
    return PAGE_TEMPLATE.format(
        count=len(users),
        rows=rows,
        generated=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home-base", default="/home/almalinux", type=Path)
    parser.add_argument("--domain", default="almapeople.org")
    parser.add_argument("--out", default="/srv/people/site/index.html", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    users = collect_users(args.home_base)
    page = render(users, args.domain)

    tmp = args.out.with_suffix(args.out.suffix + ".tmp")
    tmp.write_text(page, encoding="utf-8")
    tmp.replace(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
