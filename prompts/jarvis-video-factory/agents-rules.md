<!-- source: gogonaver12-bot/jarvis-video-factory AGENTS.md (사용자 승인으로 공개 통합, 2026-11-26) -->
# JARVIS Codex instructions

Preserve existing behavior and inspect relevant source before edits. Respond in Korean.
Budget is KRW 0: no paid APIs, billing changes, automatic publishing, or quota bypass.
Keep credentials in environment variables or GitHub Secrets; never print their values.
Use feature branches and reviewable PRs. Follow existing tests and validate real outputs.

## REA integration

REA means https://github.com/morluto/rea (Reverse Engineer Anything).
Read docs/rea_setup_ko.md before using it. This repository pins rea-agents 6.7.0.
REA is an optional analysis tool; video production must work independently of it.
When asked to connect REA, run `node tools/rea.mjs check`, then `plan`, then `setup`,
then `doctor` in the actual Codex host. Setup is scoped to Codex and installs the
official matching workflow instructions. Restart/reconnect Codex to expose MCP tools.
Do not equate a successful doctor report with a live MCP session.
Do not install Hopper or other paid providers. For native analysis use an existing
authorized free Ghidra installation; report missing prerequisites honestly.
Analyze software the owner owns or is authorized to examine. Record evidence,
limitations and proposed changes before implementing and testing features.
REA does not generate videos or improve video quality just by being installed.

## Verification

Check dependencies and syntax, then run relevant smoke tests. Preserve Korean text
and paths containing spaces. Windows launchers must support PowerShell 5.1/CMD.
Report exactly what executed, outputs, test results, and host access limitations.
