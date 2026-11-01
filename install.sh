#!/usr/bin/env sh
# Copy showcase-progress into the skill folders that agents read.
#   ~/.claude/skills  -> Claude Code
#   ~/.agents/skills  -> Codex, Gemini CLI, OpenClaw and other Agent Skills tools
# Usage: ./install.sh [target-dir ...]
set -eu

here=$(cd "$(dirname "$0")" && pwd)
if [ "$#" -eq 0 ]; then
  set -- "$HOME/.claude/skills" "$HOME/.agents/skills"
fi

for root in "$@"; do
  dest="$root/showcase-progress"
  mkdir -p "$dest"
  for item in SKILL.md PROMPT.md PROMPT.zh-CN.md LICENSE scripts references agents; do
    cp -R "$here/$item" "$dest/"
  done
  echo "installed -> $dest"
done

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "warning: Python 3.8+ not found on PATH; the skill's script needs it." >&2
fi
