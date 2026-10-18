"""Fetch public WakaTime stats and render them into README.md between markers."""
import json
import re
import urllib.request
from pathlib import Path

USER_ID = "aa611116-2b27-42b6-864a-656d4d272a11"
URL = f"https://wakatime.com/api/v1/users/{USER_ID}/stats"
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!--WAKATIME:START-->", "<!--WAKATIME:END-->"
BAR_WIDTH = 25


def bar(percent: float) -> str:
    filled = round(percent / 100 * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def section(rows, limit=6):
    lines = []
    for r in rows[:limit]:
        lines.append(f"{r['name']:<14} {r['text']:<18} {bar(r['percent'])} {r['percent']:5.1f} %")
    return "\n".join(lines)


def render(d) -> str:
    since = d.get("start", "")[:10]
    head = f"**Total:** {d['human_readable_total_including_other_language']}"
    head += f" · **Daily average:** {d['human_readable_daily_average_including_other_language']}"
    if since:
        head += f" · since {since}"
    parts = [head, "", "```text", "Languages", section(d["languages"])]
    if d.get("editors"):
        parts += ["", "Editors", section(d["editors"], 3)]
    parts.append("```")
    return "\n".join(parts)


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "readme-wakatime"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)["data"]
    readme = README.read_text(encoding="utf-8")
    block = f"{START}\n{render(data)}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, readme, flags=re.S)
    README.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    main()
