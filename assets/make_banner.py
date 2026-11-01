"""Render the README banners (light/dark SVG) and the social preview PNG.

The bar in the banner is a real ledger state: segment widths are the
subtasks' estimated minutes, and the percentage comes from scripts/progress.py.
Run: python assets/make_banner.py   (the PNG needs Pillow)
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("progress", os.path.join(ROOT, "scripts", "progress.py"))
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)

# Same plan as examples/plan.json and the demo: Q1-Q3 done, Q4 counted 1/3.
SUBTASKS = [
    {"id": "Q1", "title": "Map auth flow", "est": 25, "state": "done", "actual": 35},
    {"id": "Q2", "title": "Reset endpoint", "est": 70, "state": "done", "actual": 100},
    {"id": "Q3", "title": "Email", "est": 45, "state": "done", "actual": 50},
    {"id": "Q4", "title": "Reset page", "est": 80, "state": "doing", "count": [1, 3]},
    {"id": "Q5", "title": "Tests", "est": 40, "state": "todo"},
    {"id": "Q6", "title": "Docs", "est": 15, "state": "todo"},
]
STATE = {"subtasks": SUBTASKS}
INFO = progress.totals(STATE)
PERCENT = "%.1f%%" % (INFO["fraction"] * 100)

THEMES = {
    "dark": {
        "bg1": "#0b1020", "bg2": "#141d3a", "text": "#f8fafc", "muted": "#94a3b8",
        "done": "#34d399", "part": "#fbbf24", "todo": "#334155", "edge": "#475569",
    },
    "light": {
        "bg1": "#ffffff", "bg2": "#eef2ff", "text": "#0f172a", "muted": "#475569",
        "done": "#059669", "part": "#d97706", "todo": "#e2e8f0", "edge": "#cbd5e1",
    },
}

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"


def segments(x0: float, width: float, gap: float):
    total = sum(s["est"] for s in SUBTASKS)
    usable = width - gap * (len(SUBTASKS) - 1)
    x = x0
    for sub in SUBTASKS:
        w = usable * sub["est"] / total
        yield sub, x, w
        x += w + gap


def svg(theme: str) -> str:
    c = THEMES[theme]
    W, H = 1280, 360
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="showcase-progress: a progress bar your AI agent can\'t fake">' % (W, H, W, H),
        "<defs>"
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
        '<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="10" height="10" fill="%s" opacity="0.18"/>'
        '<rect width="4" height="10" fill="%s" opacity="0.35"/></pattern>'
        "</defs>" % (c["bg1"], c["bg2"], c["part"], c["part"]),
        '<rect width="%d" height="%d" rx="18" fill="url(#bg)"/>' % (W, H),
        '<text x="80" y="78" font-family="%s" font-size="15" letter-spacing="2.5" fill="%s">'
        "AGENT SKILL · CLAUDE CODE · CODEX · GEMINI CLI · OPENCLAW</text>" % (MONO, c["muted"]),
        '<text x="76" y="150" font-family="%s" font-size="68" font-weight="700" fill="%s">'
        "showcase-progress</text>" % (SANS, c["text"]),
        '<text x="80" y="198" font-family="%s" font-size="28" fill="%s">'
        "A progress bar your AI agent can\u2019t fake.</text>" % (SANS, c["muted"]),
        '<text x="1200" y="150" text-anchor="end" font-family="%s" font-size="64" font-weight="700" fill="%s">'
        "%s</text>" % (MONO, c["done"], PERCENT),
        '<text x="1200" y="196" text-anchor="end" font-family="%s" font-size="22" fill="%s">'
        "%s left at current pace</text>" % (MONO, c["muted"], progress.fmt_minutes(INFO["remaining"])),
    ]
    y, h = 248, 34
    for sub, x, w in segments(80, 1120, 8):
        if sub["state"] == "done":
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="6" fill="%s"/>' % (x, y, w, h, c["done"]))
        elif sub.get("count"):
            k, n = sub["count"]
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="6" fill="url(#hatch)" stroke="%s"/>'
                       % (x, y, w, h, c["part"]))
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="6" fill="%s"/>'
                       % (x, y, w * k / n, h, c["part"]))
        else:
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="6" fill="%s" stroke="%s"/>'
                       % (x, y, w, h, c["todo"], c["edge"]))
        label = "%s · %s" % (sub["id"], progress.fmt_minutes(sub["est"]))
        if sub.get("count"):
            label += " · %d/%d" % tuple(sub["count"])
        out.append('<text x="%.1f" y="%d" font-family="%s" font-size="18" fill="%s">%s</text>'
                   % (x + 2, y + h + 28, MONO, c["muted"], label))
    out.append('<text x="80" y="%d" font-family="%s" font-size="17" fill="%s">'
               "segment width = estimated time · only finished or counted work fills the bar</text>"
               % (y + h + 64, SANS, c["muted"]))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def png(path: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    c = THEMES["dark"]
    W, H = 1280, 640
    img = Image.new("RGB", (W, H), c["bg1"])
    draw = ImageDraw.Draw(img)
    # vertical-ish gradient
    top, bottom = [int(c["bg1"][i:i + 2], 16) for i in (1, 3, 5)], [int(c["bg2"][i:i + 2], 16) for i in (1, 3, 5)]
    for row in range(H):
        t = row / H
        draw.line([(0, row), (W, row)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))

    def font(names, size):
        for name in names:
            for folder in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"):
                candidate = os.path.join(folder, name)
                if os.path.exists(candidate):
                    return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()

    bold = font(["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 84)
    sans = font(["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf"], 36)
    mono = font(["consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"], 20)
    mono_big = font(["consolab.ttf", "DejaVuSansMono-Bold.ttf", "Menlo.ttc"], 76)
    small = font(["consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"], 18)

    draw.text((80, 96), "AGENT SKILL · CLAUDE CODE · CODEX · GEMINI CLI · OPENCLAW", font=small, fill=c["muted"])
    draw.text((76, 150), "showcase-progress", font=bold, fill=c["text"])
    draw.text((80, 270), "A progress bar your AI agent can\u2019t fake.", font=sans, fill=c["muted"])

    y, h = 380, 48
    for sub, x, w in segments(80, 1120, 10):
        box = [x, y, x + w, y + h]
        if sub["state"] == "done":
            draw.rounded_rectangle(box, 8, fill=c["done"])
        elif sub.get("count"):
            k, n = sub["count"]
            draw.rounded_rectangle(box, 8, outline=c["part"], width=2)
            draw.rounded_rectangle([x, y, x + w * k / n, y + h], 8, fill=c["part"])
        else:
            draw.rounded_rectangle(box, 8, fill=c["todo"], outline=c["edge"], width=2)
        label = "%s · %s" % (sub["id"], progress.fmt_minutes(sub["est"]))
        draw.text((x + 2, y + h + 14), label, font=mono, fill=c["muted"])

    draw.text((80, 520), PERCENT, font=mono_big, fill=c["done"])
    draw.text((420, 548), "time-weighted · evidence-based · self-correcting ETA", font=mono, fill=c["muted"])
    img.save(path, optimize=True)


def main() -> None:
    for theme in THEMES:
        path = os.path.join(HERE, "banner-%s.svg" % theme)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(svg(theme))
        print("wrote", path)
    try:
        path = os.path.join(HERE, "social-preview.png")
        png(path)
        print("wrote", path)
    except ImportError:
        print("Pillow not installed; skipped social-preview.png")


if __name__ == "__main__":
    main()
