"""Fetch public WakaTime stats, render a languages SVG and the summary into README.md."""
import json
import re
import urllib.request
from html import escape
from pathlib import Path

USER_ID = "aa611116-2b27-42b6-864a-656d4d272a11"
URL = f"https://wakatime.com/api/v1/users/{USER_ID}/stats"
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SVG = ROOT / "assets" / "languages.svg"
START, END = "<!--WAKATIME:START-->", "<!--WAKATIME:END-->"

# Markup, config and data formats WakaTime counts as "languages"
NOT_PROGRAMMING = {
    "markdown", "css", "scss", "sass", "less", "html", "json", "jsonc", "json5", "yaml", "toml",
    "xml", "ini", "text", "other", "csv", "svg", "git", "git config", "gitignore file",
    "docker", "dockerfile", "makefile", "batch", "log", "properties", "env", "restructuredtext",
    "ignore list", "tex", "unknown", "powershell", "astro", "vue", "svelte",
}
LIMIT = 5

BG, TEXT, MUTED, TRACK = "#0d1117", "#e6edf3", "#8b949e", "#161b22"
BAR = "#5a87bc"  # WakaTime mid blue, same as the heatmap


def languages_svg(langs) -> str:
    width, row_h, top, bar_x, bar_w = 520, 28, 34, 230, 200
    top_secs = langs[0]["total_seconds"]
    rows = []
    for i, l in enumerate(langs):
        y = top + i * row_h
        w = max(2, round(l["total_seconds"] / top_secs * bar_w))
        rows.append(
            f'<text x="20" y="{y + 12}" fill="{TEXT}">{escape(l["name"])}</text>'
            f'<text x="120" y="{y + 12}" fill="{MUTED}">{escape(l["text"])}</text>'
            f'<rect x="{bar_x}" y="{y + 2}" width="{bar_w}" height="12" rx="3" fill="{TRACK}"/>'
            f'<rect x="{bar_x}" y="{y + 2}" width="{w}" height="12" rx="3" fill="{BAR}"/>'
            f'<text x="{width - 20}" y="{y + 12}" fill="{MUTED}" text-anchor="end">{l["percent"]:.1f} %</text>'
        )
    height = top + len(langs) * row_h + 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<rect width="100%" height="100%" rx="6" fill="{BG}"/>'
            f'<g font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="12">'
            f'<text x="20" y="22" fill="{MUTED}" font-size="11" letter-spacing="1">LANGUAGES</text>'
            + "".join(rows) + "</g></svg>")


def render(d) -> str:
    return '<img src="assets/languages.svg" alt="Languages">'


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "readme-wakatime"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)["data"]
    langs = [l for l in data["languages"] if l["name"].lower() not in NOT_PROGRAMMING][:LIMIT]
    SVG.parent.mkdir(exist_ok=True)
    SVG.write_text(languages_svg(langs), encoding="utf-8")

    readme = README.read_text(encoding="utf-8")
    block = f"{START}\n{render(data)}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, readme, flags=re.S)
    README.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    main()
