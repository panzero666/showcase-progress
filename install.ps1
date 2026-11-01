# Copy showcase-progress into the skill folders that agents read.
#   ~\.claude\skills  -> Claude Code
#   ~\.agents\skills  -> Codex, Gemini CLI, OpenClaw and other Agent Skills tools
# Usage: .\install.ps1 [-Targets <dir>, <dir>]
param(
    [string[]]$Targets = @(
        (Join-Path $HOME ".claude\skills"),
        (Join-Path $HOME ".agents\skills")
    )
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$items = "SKILL.md", "PROMPT.md", "PROMPT.zh-CN.md", "LICENSE", "scripts", "references", "agents"

# `powershell -File install.ps1 -Targets a,b` passes "a,b" as one string
$Targets = $Targets | ForEach-Object { $_ -split "," } | Where-Object { $_ }

foreach ($root in $Targets) {
    $dest = Join-Path $root "showcase-progress"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($item in $items) {
        Copy-Item -Recurse -Force (Join-Path $here $item) $dest
    }
    Write-Output "installed -> $dest"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Warning "Python 3.8+ not found on PATH; the skill's script needs it."
}
