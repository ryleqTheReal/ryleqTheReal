"""Render the WakaTime card (totals, languages, activity heatmap) as light and dark SVGs.

GitHub strips all CSS from READMEs, so the container is drawn as SVG; the README picks
the variant with <picture> and prefers-color-scheme. Layout follows the semjon-it mails:
bordered card, 32px padding, navy/gray text.
The heatmap needs WAKATIME_API_KEY (daily data is private); the rest is public.
"""
import base64
import datetime as dt
import hashlib
import json
import os
import re
import urllib.request
from html import escape
from pathlib import Path

USER_ID = "aa611116-2b27-42b6-864a-656d4d272a11"
STATS_URL = f"https://wakatime.com/api/v1/users/{USER_ID}/stats"
DAYS_URL = "https://wakatime.com/api/v1/users/current/insights/days/last_year"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
README = ASSETS.parent / "README.md"

# Markup, config and data formats and frameworks WakaTime counts as "languages"
NOT_PROGRAMMING = {
    "markdown", "css", "scss", "sass", "less", "html", "json", "jsonc", "json5", "yaml", "toml",
    "xml", "ini", "text", "other", "csv", "svg", "git", "git config", "gitignore file",
    "docker", "dockerfile", "makefile", "batch", "log", "properties", "env", "restructuredtext",
    "ignore list", "tex", "unknown", "powershell", "astro", "vue", "svelte",
}
LIMIT = 5

THEMES = {
    "light": {
        "card": "#ffffff", "line": "#E2E6EC", "text": "#0B1530", "muted": "#5A6270",
        "accent": "#0C55F7", "track": "#EEF1F5",
        "levels": ["#EEF1F5", "#C7D7FD", "#8DAEFB", "#4A7FF9", "#0C55F7", "#0B1530"],
    },
    "dark": {
        "card": "#0d1117", "line": "#30363d", "text": "#e6edf3", "muted": "#8b949e",
        "accent": "#0C55F7", "track": "#161b22",
        # WakaTime's own heatmap steps, dark blue -> white
        "levels": ["#161b22", "#2c3e55", "#3d618d", "#5a87bc", "#9cb8db", "#f2f6fb"],
    },
}
FONT = "'Segoe UI',Arial,Helvetica,sans-serif"
PAD = 32
CELL, GAP = 11, 3
STEP = CELL + GAP


def get(url: str, headers=None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "readme-wakatime", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def fetch_days(key: str) -> dict:
    token = base64.b64encode(key.encode()).decode()
    days = json.loads(get(DAYS_URL, {"Authorization": f"Basic {token}"}))["data"]["days"]
    return {dt.date.fromisoformat(d["date"]): d.get("total", 0) or 0 for d in days}


# ---- pieces, each returns (svg, height) drawn at (0, 0) with the given width ----

def languages(langs, width, t):
    row_h, top = 28, 26
    name_w, time_w, pct_w = 110, 120, 56
    bar_x, bar_w = name_w + time_w, width - name_w - time_w - pct_w
    top_secs = langs[0]["total_seconds"]
    out = [f'<text x="0" y="12" fill="{t["muted"]}" font-size="12" letter-spacing="1">LANGUAGES</text>']
    for i, l in enumerate(langs):
        y = top + i * row_h
        w = max(2, round(l["total_seconds"] / top_secs * bar_w))
        out.append(
            f'<text x="0" y="{y + 12}" fill="{t["text"]}" font-size="14">{escape(l["name"])}</text>'
            f'<text x="{name_w}" y="{y + 12}" fill="{t["muted"]}" font-size="14">{escape(l["text"])}</text>'
            f'<rect x="{bar_x}" y="{y + 2}" width="{bar_w}" height="12" rx="3" fill="{t["track"]}"/>'
            f'<rect x="{bar_x}" y="{y + 2}" width="{w}" height="12" rx="3" fill="{t["accent"]}"/>'
            f'<text x="{width}" y="{y + 12}" fill="{t["muted"]}" font-size="14" text-anchor="end">{l["percent"]:.1f} %</text>')
    return "".join(out), top + len(langs) * row_h


def totals(stats, days, width, t):
    """Key figures: large bold hours, a plain caption underneath."""
    year = dt.date.today().year
    since = stats.get("human_readable_range", "").replace("since ", "")
    since = re.sub(r"(\w+) \d+ (\d{4})", r"\1 \2", since)  # "Oct 24 2022" -> "Oct 2022"
    items = [(stats["total_seconds_including_other_language"], f"coded since {since}" if since else "coded in total")]
    if days:
        items.insert(0, (sum(s for d, s in days.items() if d.year == year), f"coded in {year}"))
    col = width / len(items)
    out = "".join(
        f'<text x="{i * col}" y="28" fill="{t["text"]}" font-size="30" font-weight="bold">{int(secs // 3600):,}'
        f'<tspan font-size="18" font-weight="normal" fill="{t["muted"]}"> hrs</tspan></text>'
        f'<text x="{i * col}" y="52" fill="{t["muted"]}" font-size="14">{caption}</text>'
        for i, (secs, caption) in enumerate(items))
    return out, 56


def heatmap(days, t):
    end = max(days) if days else dt.date.today()
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    top = sorted(days.values())[int(len(days) * 0.97)] if days else 0  # ignore outliers
    left, head = 30, 16

    def level(secs):
        if secs <= 0:
            return 0
        return min(5, 1 + int(secs / top * 5)) if top else 1

    cells, labels = [], []
    day, week, last_month = start, 0, None
    while day <= end:
        row = (day.weekday() + 1) % 7
        if row == 0 and day.month != last_month:
            labels.append(f'<text x="{left + week * STEP}" y="10">{day.strftime("%b")}</text>')
            last_month = day.month
        secs = days.get(day, 0)
        cells.append(f'<rect x="{left + week * STEP}" y="{head + row * STEP}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{t["levels"][level(secs)]}"><title>{day}: {secs / 3600:.1f} h</title></rect>')
        if row == 6:
            week += 1
        day += dt.timedelta(days=1)
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        labels.append(f'<text x="0" y="{head + row * STEP + 9}">{name}</text>')

    width = left + week * STEP + CELL
    ly = head + 7 * STEP + 8
    lx = width - 6 * STEP - 30
    labels.append(f'<text x="{lx - 30}" y="{ly + 9}">Less</text><text x="{lx + 6 * STEP + 2}" y="{ly + 9}">More</text>')
    legend = "".join(f'<rect x="{lx + i * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>'
                     for i, c in enumerate(t["levels"]))
    svg = (f'<g font-size="11" fill="{t["muted"]}">{"".join(labels)}</g>' + "".join(cells) + legend)
    return svg, width, ly + CELL


def card(stats, langs, days, theme):
    t = THEMES[theme]
    hm, inner, hm_h = heatmap(days, t)
    width = inner + 2 * PAD
    parts, y = [], PAD

    for piece, h in (totals(stats, days, inner, t), languages(langs, inner, t)):
        parts.append(f'<g transform="translate(0 {y})">{piece}</g>')
        y += h + 24
    parts.append(f'<g transform="translate(0 {y})">{hm}</g>')
    y += hm_h + PAD

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{y}" viewBox="0 0 {width} {y}">'
            f'<rect x=".5" y=".5" width="{width - 1}" height="{y - 1}" fill="{t["card"]}" stroke="{t["line"]}"/>'
            f'<g font-family="{FONT}" transform="translate({PAD} 0)">{"".join(parts)}</g></svg>')


def main():
    stats = json.loads(get(STATS_URL))["data"]
    langs = [l for l in stats["languages"] if l["name"].lower() not in NOT_PROGRAMMING][:LIMIT]
    key = os.environ.get("WAKATIME_API_KEY")
    if not key:
        print("WAKATIME_API_KEY not set, heatmap stays empty")
    days = fetch_days(key) if key else {}
    ASSETS.mkdir(exist_ok=True)
    readme = README.read_text(encoding="utf-8")
    for theme in THEMES:
        svg = card(stats, langs, days, theme)
        (ASSETS / f"wakatime-{theme}.svg").write_text(svg, encoding="utf-8")
        # content hash in the URL, otherwise GitHub's image cache keeps showing old stats
        version = hashlib.sha1(svg.encode()).hexdigest()[:10]
        readme = re.sub(rf'assets/wakatime-{theme}\.svg(\?v=\w+)?', f"assets/wakatime-{theme}.svg?v={version}", readme)
    README.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
