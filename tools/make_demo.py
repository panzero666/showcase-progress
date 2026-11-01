"""Render assets/demo.svg from a real run of scripts/progress.py.

Every line in the image is actual script output; nothing is typed by hand.
Run: python tools/make_demo.py
"""

import contextlib
import importlib.util
import io
import os
import tempfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("progress", os.path.join(ROOT, "scripts", "progress.py"))
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)

STEPS = [
    ("init --plan examples/plan.json", "09:00"),
    ('update "Q1=done" --took 35m --brief', "09:35"),
    ('update "Q2=done" --took 1h40m --evidence "202 + token row" --brief', "11:15"),
    ('update "Q3=done" --took 50m --brief', "12:05"),
    ('update "Q4=doing" --count 1/3 --brief', "12:40"),
    ("render", "12:40"),
]


def run(state: str, command: str, clock: str) -> str:
    import shlex
    argv = ["--state", state] + shlex.split(command) + ["--now", "2026-11-01T%s:00" % clock]
    if argv[2] == "init":
        argv += ["--started", "2026-11-01T09:00:00"]
    out = io.StringIO()
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        with contextlib.redirect_stdout(out):
            progress.main(argv)
    finally:
        os.chdir(cwd)
    return out.getvalue().rstrip("\n")


def main() -> None:
    state = os.path.join(tempfile.mkdtemp(), "state.json")
    lines = []                      # (kind, text)
    for command, clock in STEPS:
        lines.append(("cmd", "$ progress.py " + command))
        for row in run(state, command, clock).splitlines():
            lines.append(("out", row))
        lines.append(("gap", ""))
    lines.pop()

    line_h, pad, char_w = 22, 20, 8.4
    width = int(max(len(t) for _, t in lines) * char_w + pad * 2 + 10)
    width = max(width, 760)
    height = 44 + pad + line_h * len(lines) + pad
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        % (width, height, width, height),
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;"
        "font-size:14px;white-space:pre}"
        ".cmd{fill:#7dd3fc}.out{fill:#e5e7eb}"
        ".l{opacity:0;animation:show .01s forwards}"
        "@keyframes show{to{opacity:1}}"
        "</style>",
        '<rect width="100%" height="100%" rx="10" fill="#0f172a"/>',
        '<circle cx="22" cy="20" r="6" fill="#f87171"/>'
        '<circle cx="42" cy="20" r="6" fill="#fbbf24"/>'
        '<circle cx="62" cy="20" r="6" fill="#34d399"/>',
        '<text x="%d" y="25" fill="#94a3b8" text-anchor="middle" class="out" style="fill:#94a3b8">'
        "showcase-progress</text>" % (width // 2),
    ]
    y = 44 + pad
    delay, block = 0.3, 0
    for kind, text in lines:
        if kind == "cmd":
            delay += 0.9 if block else 0
            block += 1
        if text:
            parts.append(
                '<text x="%d" y="%d" class="l %s" style="animation-delay:%.1fs">%s</text>'
                % (pad, y, kind, delay, escape(text))
            )
        if kind == "cmd":
            delay += 0.5
        y += line_h
    parts.append("</svg>")
    out_path = os.path.join(ROOT, "assets", "demo.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(parts) + "\n")
    print("\n".join(t for _, t in lines))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
