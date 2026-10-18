"""Render last year's WakaTime daily activity as an SVG heatmap (WakaTime colors).

Needs WAKATIME_API_KEY: daily data is not public, unlike the all-time stats.
"""
import base64
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

URL = "https://wakatime.com/api/v1/users/current/insights/days/last_year"
OUT = Path(__file__).resolve().parent.parent / "assets" / "activity.svg"
BADGES = OUT.with_name("badges.svg")
USER_ID = "aa611116-2b27-42b6-864a-656d4d272a11"
BADGE_URL = f"https://wakatime.com/badge/user/{USER_ID}.svg"
STATS_URL = f"https://wakatime.com/api/v1/users/{USER_ID}/stats"

BG = "#0d1117"
TEXT = "#8b949e"
# empty, then the 5 WakaTime intensity steps (dark blue -> white)
LEVELS = ["#161b22", "#2c3e55", "#3d618d", "#5a87bc", "#9cb8db", "#f2f6fb"]
CELL, GAP = 11, 3
LEFT, TOP = 34, 30


def fetch_days(key: str) -> dict[dt.date, float]:
    token = base64.b64encode(key.encode()).decode()
    req = urllib.request.Request(URL, headers={"Authorization": f"Basic {token}", "User-Agent": "readme-wakatime"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        days = json.load(resp)["data"]["days"]
    return {dt.date.fromisoformat(d["date"]): d.get("total", 0) or 0 for d in days}


def level(seconds: float, top: float) -> int:
    if seconds <= 0:
        return 0
    return min(5, 1 + int(seconds / top * 5)) if top else 1


def render(days: dict[dt.date, float]) -> str:
    end = max(days) if days else dt.date.today()
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    top = sorted(days.values())[int(len(days) * 0.97)] if days else 0  # ignore outliers

    cells, months = [], []
    day, week, last_month = start, 0, None
    while day <= end:
        row = (day.weekday() + 1) % 7
        if row == 0 and day.month != last_month:
            months.append((week, day.strftime("%b")))
            last_month = day.month
        x, y = LEFT + week * (CELL + GAP), TOP + row * (CELL + GAP)
        secs = days.get(day, 0)
        hrs = f"{secs / 3600:.1f} h"
        cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{LEVELS[level(secs, top)]}"><title>{day}: {hrs}</title></rect>')
        if row == 6:
            week += 1
        day += dt.timedelta(days=1)

    width = LEFT + (week + 1) * (CELL + GAP) + 10
    height = TOP + 7 * (CELL + GAP) + 30
    text = [f'<text x="{LEFT + w * (CELL + GAP)}" y="{TOP - 8}">{m}</text>' for w, m in months]
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        text.append(f'<text x="2" y="{TOP + row * (CELL + GAP) + 9}">{name}</text>')
    lx, ly = width - 10 - 6 * (CELL + GAP) - 30, height - 18
    text.append(f'<text x="{lx - 30}" y="{ly + 9}">Less</text>')
    legend = [f'<rect x="{lx + i * (CELL + GAP)}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>'
              for i, c in enumerate(LEVELS)]
    text.append(f'<text x="{lx + 6 * (CELL + GAP) + 2}" y="{ly + 9}">More</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<rect width="100%" height="100%" rx="6" fill="{BG}"/>'
            f'<g font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="10" fill="{TEXT}">'
            + "".join(text) + "</g>" + "".join(cells) + "".join(legend) + "</svg>")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "readme-wakatime"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def badge(label: str, value: str, icon: str) -> tuple[str, float]:
    """Shields-style badge matching the official WakaTime one; returns (svg group, width)."""
    lw = 24 + len(label) * 6.7 + 6
    vw = 10 + len(value) * 5.9
    w = lw + vw
    return (f'<clipPath id="r{label[0]}"><rect width="{w}" height="20" rx="3"/></clipPath>'
            f'<g clip-path="url(#r{label[0]})"><rect width="{lw}" height="20" fill="#555"/>'
            f'<rect x="{lw}" width="{vw}" height="20" fill="#007ec6"/>'
            f'<rect width="{w}" height="20" fill="url(#smooth)"/></g>'
            f'<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">'
            f'{icon}'
            f'<text x="{(19 + lw) / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>'
            f'<text x="{(19 + lw) / 2}" y="14">{label}</text>'
            f'<text x="{lw + vw / 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>'
            f'<text x="{lw + vw / 2}" y="14">{value}</text></g>'), w


def render_badges(width: int) -> str:
    """Daily average left, all-time total right, spanning exactly the heatmap width."""
    official = get(BADGE_URL)
    icon = re.search(r"<image .*?/>", official).group(0)
    total = re.findall(r">([^<]*hrs?[^<]*)</text>", official)[0]
    avg = json.loads(get(STATS_URL))["data"]["human_readable_daily_average_including_other_language"]
    left, _ = badge("daily average", avg, icon)
    right, rw = badge("wakatime", total, icon)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="20" viewBox="0 0 {width} 20">'
            '<linearGradient id="smooth" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
            '<stop offset="1" stop-opacity=".1"/></linearGradient>'
            f'<g>{left}</g><g transform="translate({width - rw} 0)">{right}</g></svg>')


def main():
    OUT.parent.mkdir(exist_ok=True)
    key = os.environ.get("WAKATIME_API_KEY")
    if key:
        OUT.write_text(render(fetch_days(key)), encoding="utf-8")
    else:
        print("WAKATIME_API_KEY not set, skipping heatmap")
    if OUT.exists():
        width = int(re.search(r'width="(\d+)"', OUT.read_text(encoding="utf-8")).group(1))
        BADGES.write_text(render_badges(width), encoding="utf-8")


if __name__ == "__main__":
    main()
