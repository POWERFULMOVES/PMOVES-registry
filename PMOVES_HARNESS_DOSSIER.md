# PMOVES Harness Dossier

> What each coding harness brings to PMOVES.AI, and what PMOVES has forked or built to enhance it.
> This fork of `agentclientprotocol/registry` is the PMOVES harness registry, home of the HyPeRAGInTZ, so the dossier lives here beside the `agent.json` entries.

**Status:** seeded 2026-10-11 by SPARK-CLAUDE. Facts were measured from the PMOVES.AI monorepo, this registry's `origin/main` and `gh repo list POWERFULMOVES`; anything not measured says so.
**Companion:** `pmoves/docs/TAC/TAC_HARNESS_OVERLAY_MAP.md` in PMOVES.AI (PR #3347, 5090-CLAUDE) says *how* PMOVES connects to each harness: its native surface and overlay seam. This dossier says *why* each harness is worth connecting and *what we added*. A harness PR cites a row in both.

Operator brief (2026-10-11): "note what each harness brings to table as well as the enhancements for example crush has vhs and other repos forked to enhance."

## How to read a card

| Field | Meaning |
|---|---|
| **Brings** | The harness's native strengths, cited from its own README or docs. This is why it earns a seat in the Birkeland current: parallel filaments, not a pyramid. |
| **PMOVES fork** | Our fork of the harness itself: repo, tracked branch and PMOVES release tag. |
| **Enhancement forks** | Companion repos forked to extend it (Crush: vhs, gum, catwalk, keygen). |
| **ACP entry** | The directory in this registry, and its state (`listed`, `quarantined`, or `absent`). |
| **Identity** | Signing card(s) and the per-node Cipher `agentId` from `pmoves/configs/node-vocabulary.yaml`. Without a Cipher id, the harness writes memory as `bootstrap`. |
| **Gaps** | Measured holes. Each one is an improvement lane. |

## Cards

### Crush (Charm)
- **Brings** (`PMOVES-crush/README.md`):
  - multi-model, with provider switching mid-session;
  - session-based work;
  - LSP-enhanced context;
  - MCP over http, stdio and sse;
  - a TUI built on the Charm stack.
- **PMOVES fork:** `PMOVES-crush` (parent `charmbracelet/crush`, branch `PMOVES.AI-Edition-Hardened`), release `v0.91.2-pmoves.2`.
  - The headline addition is **`crush acp`**: an ACP v1 JSON-RPC stdio server (initialize, session/new, load, resume, prompt, cancel).
  - It streams `agent_message_chunk` updates.
  - Its session map survives adapter restarts (`$XDG_CACHE_HOME/crush/acp-sessions.json`).
  - First fleet consumer: PMOVES-spynel.
- **Enhancement forks:** submodules of PMOVES-crush, see `PMOVES_VISUAL_ECOSYSTEM.md`, plus top-level ones.
  - `pmoves-vhs` (`charmbracelet/vhs`): terminal recording as code. Tapes: `cipher-memory-smoke.tape`, `crush-pmoves-bringup.tape`, `crush-pmoves-session.tape`. These are reproducible demo and smoke evidence. On knuckles, a chromium-sandbox wrapper fixes headless capture.
  - `pmoves-catwalk` (`charmbracelet/catwalk`): the model catalog, with a TensorZero provider so Crush routes through the fleet gateway. The go.mod `replace` is gated off for CI.
  - `pmoves-gum` (`charmbracelet/gum`): TUI scripting for launchers. Customizations are *planned*.
  - `pmoves-keygen` (`charmbracelet/keygen`): a top-level submodule carrying the signing-card CLI (`cmd/keygen-cli`) and a CI gate. Crush tooling is how cards get keys.
  - `pmoves-glow` (`charmbracelet/glow`): forked, but no use measured yet.
- **ACP entry:** `crush-acp/` (PMOVES fork binaries with sha256). It is **quarantined** in `quarantine.json` because its `initialize` declares no `authMethods`.
- **Identity:**
  - The fleet card is `crush` (◇).
  - Per-node: SPARK gets `spark-crush` (PR `feat/spark-crush-identity`, 2026-10-11).
  - Knuckles has the registry id `crush_glm52` but no Cipher id.
- **Gaps:**
  - add `authMethods` to `crush acp`, which lifts the quarantine;
  - the vhs "CI regenerates GIFs on release" job is planned, not built;
  - gum customizations are planned;
  - glow is unused;
  - the fork is `sync:false` (untriaged) in `fork_registry.json`.

### Claude Code (Anthropic)
- **Brings:**
  - hooks;
  - skills;
  - subagents;
  - plugins;
  - layered settings, managed > `--settings` > local > project > user, with permission lists merged across scopes;
  - `@path` imports (4 hops);
  - AGENTS.md support;
  - `--mcp-config`, `--agent` and `--append-system-prompt`.

  The settings facts were verified against the official settings and memory docs on 2026-10-11.
- **PMOVES fork:** `PMOVES-claude-code` exists on GitHub only and is not a submodule. Claude Code is consumed upstream.
- **Enhancement forks:**
  - `Pmoves-claude-code-damage-control` (disler): Known Roads and the zero-access `.env*` guard in `.claude/hooks/damage-control/`.
  - `PMOVESxDISLER--claude-code-hooks-mastery`.
  - `Pmoves-claude-mem`.
  - `Pmoves-Claude-skills` (`anthropics/skills`, nested in `skills/PMOVES-skills/sources/`).
  - `Pmoves-claude-d3js-skill`.
  - `PMOVES-agent-sandbox-skill`.
  - `pmoves-fork-repository-skill`.
  - `Pmoves-claude-agent-acp` (`agentclientprotocol/claude-agent-acp`).
- **ACP entry:** `claude-acp/` (upstream adapter).
- **Identity:** one card and Cipher id per node: `4090-claude`, `5090-claude`, `b850-claude`, `spark-claude`, `z890-claude`. All five are bound in node-vocabulary.
- **Gaps:**
  - the ACP adapter fork is not wired to a launcher;
  - a session started outside `claude-pmoves*.sh` runs as `bootstrap`, so the launcher is the identity path.

### Hermes (NousResearch)
- **Brings** (`PMOVES-hermes-agent/README.md`):
  - a closed learning loop: self-created skills and FTS5 session search;
  - a messaging gateway for Telegram, Discord, Slack, WhatsApp, Signal and email;
  - a cron scheduler;
  - subagent delegation;
  - agentskills.io compatibility;
  - a native ACP adapter (`acp_adapter/`, `hermes-acp`), rated `acp_conformant` in the 2026-09-22 citizenship audit.
- **PMOVES fork:** `PMOVES-hermes-agent` (branch `PMOVES.AI-Edition-Hardened`, `sync:true`, tag v0.21.4).
- **Enhancement forks:**
  - `pmoves-hermes-agent-self-evolution` (skill and prompt evolution);
  - `Pmoves-hermes-mod` (Pinokio mod).

  Both exist only on GitHub, with no use measured.
- **ACP entry:** **absent**. The adapter is conformant, so this is an unfilled entry, not a missing capability.
- **Identity:** two candidate cards (`hermes`, `hermes-agent`), so there is no Cipher id. The registry row is `hermes_agent`, with affinity to 8 nodes.
- **Gaps:**
  - add a `hermes-agent/` registry entry;
  - pick one card;
  - write `PMOVES.AI_INTEGRATION.md` in the fork (missing).

### Agent Zero
- **Brings** (`PMOVES-Agent-Zero/README.md`):
  - a plugin hub with 100+ community plugins;
  - projects with isolated memory;
  - skills;
  - MCP and A2A;
  - a Dockerized Linux desktop and browser;
  - subordinate agents.
- **PMOVES fork:** `PMOVES-Agent-Zero` (branch `PMOVES.AI-Edition-Hardened`, `sync:true`).
- **Enhancement forks:**
  - `PMOVES-a0-plugins` (`agent0ai/a0-plugins`), which carries `pmoves_coding_agents` (delegates to hermes, crush, opencode and codex), `kimi_code`, `kilo_code_gateway`, `codex_provider`, `jev_router`, `typesafe_ai` and `pmoves_notes`;
  - `a0_acp` (`3clyp50/a0_acp`);
  - `PMOVES-spynel` and `space-agent`;
  - `PMOVES-A0-codex-docker`, the base image for a0-elder-melchor.
- **ACP entry:** `pmoves-agent-zero/` v1.19.0 (uvx from `POWERFULMOVES/a0_acp`). It is a PMOVES-authored entry.
- **Identity:** no Cipher id. The registry signature is `claude-opus`.
- **Gaps:**
  - `PMOVES-a0-plugins/PMOVES.AI_INTEGRATION.md` is `_TBD_` on every overlay line;
  - the Jev plugins aren't in the living docs.

### Kilo / OpenCode
- **Brings** (`PMOVES-KeYlOkODe/README.md`):
  - runs in VS Code, JetBrains and the CLI;
  - 500+ models;
  - a cloud agent;
  - native `kilo.json` config.
- **PMOVES fork:** `PMOVES-KeYlOkODe` (parent `Kilo-Org/kilocode`, `sync:true`). `cli_tools.yaml` names it the harness source of truth (v7.6.2). `pmoves-sst-opencode` is a GitHub fork of OpenCode.
- **Enhancement forks:** all on GitHub only, with use not measured:
  - `PMOVES-cloud`
  - `PMOVES-kilo-pi-provider`
  - `PMOVES-kilo-marketplace`
  - `Pmoves-kilo-design`
  - `Pmoves-vscode-extension-self-test`
  - `PMOVES-agentic-path`
  - `PMOVES-KiloMan`
- **ACP entries:** `kilo/` is linked to `kilocode_glm`; `opencode/` exists.
- **Identity:** the card is `kilocode`; there is no Cipher id.
- **Gaps:**
  - the fork has no `PMOVES.AI_INTEGRATION.md`;
  - the KiloClaw split (light claw on hosted, heavy claw on KVM using fleet GPUs) is deferred, with its plan in Cipher under spark-claude.

### Kimi (Moonshot)
- **Brings:** Kimi Code, plus the legacy kimi-cli. Two programs share the name, and which one a node runs is an operator fact. Native strengths are **not yet measured** from upstream docs.
- **PMOVES fork:** none of the harness. `Pmoves-Kimi-Dev` is the model repo, not the harness.
- **Enhancement:** the `kimi_code` Agent Zero plugin. Its launcher merges the `.kimi`, `.claude` and `.codex` skill trees.
- **ACP entry:** `kimi/` (pins the archived Python kimi-cli), deliberately unbridged.
- **Identity:** `knuckles-kimi` (card `…051`). It was the first harness to get a per-node Cipher id (2026-09-19) and is the precedent `spark-crush` follows.
- **Gaps:** there is no flavor key in node-vocabulary yet.

### Codex (OpenAI)
- **Brings:** native AGENTS.md, `config.toml` and `.agents/skills` (per #3347; **not yet verified** upstream).
- **PMOVES fork:** none of `openai/codex`. `PMOVES-A0-codex-docker` is the container base.
- **Enhancement:** the `codex_provider` Agent Zero plugin.
- **ACP entry:** `codex-acp/`.
- **Identity:** two candidate cards (`codex`, `agent-zero-codex`), so there is no Cipher id.

### Others on the bench
- **DeepSeek harness:**
  - Fork `PMOVES-deepseek-harness`, `sync:false` (upstream is a developer preview).
  - Brings a neutral hook protocol with Claude Code and Codex bridges, and a profile/bundle/patch model.
  - "Harness-registry integration pending": no entry here yet.
- **ClawZ / OpenClaw:**
  - Fork `PMOVES-ClawZ`.
  - Brings a multi-channel gateway with 47 extensions (`acpx`, `kimi-coding`).
  - Related forks: `PMOVES-NemoClaw`, `PMOVES-ClawRouter`.
- **MiniMax Code:**
  - `minimax-code/` exists (no repository field).
  - Fork `PMOVES-minimax-code` (GitHub only).
  - Related submodules: `Pmoves-minimax-cli`, `PMOVES-MiniMax-MCP`, `Pmoves-MiniMax-Provider-Verifier`.
- **Gemini:**
  - Has a signing card (`gemini`).
  - Add-on forks: `Pmoves-conductor`, `pmoves-Gemini-CLI-UI`.
  - No launcher.
- **goose and qwen-code:** listed upstream; no PMOVES fork or launcher.

## Pairings: harnesses that work as a crew

PMOVES runs several harnesses on one node at once; identity outlives the node. On SPARK the operator paired **spark-claude** with **Crush** (2026-10-11):
- Crush brings LSP context, mid-session model switching and vhs-recorded evidence.
- Claude brings hooks, subagents and the Known Roads guard.
- Each writes Cipher memory under its own id (`spark-claude`, `spark-crush`) so the crew can learn from each other without polluting `bootstrap`.

## Enhancement backlog (measured gaps → lanes)

1. `crush acp`: declare `authMethods`, then lift the `crush-acp` quarantine.
2. Add a `hermes-agent/` entry; its adapter is already conformant.
3. Add a DeepSeek harness entry once its registry integration lands.
4. Write `PMOVES.AI_INTEGRATION.md` for PMOVES-hermes-agent, PMOVES-KeYlOkODe, PMOVES-ClawZ and PMOVES-A0-codex-docker; fill PMOVES-a0-plugins' `_TBD_` lines.
5. Per-node Cipher ids for codex, hermes and kilo, after one card is chosen where there are two.
6. vhs: regenerate GIFs in CI on PMOVES-crush release; extend the tapes to other harness launchers (a cross-harness smoke reel).
7. Triage `sync:false` forks (`PMOVES-crush`, `pmoves-keygen`) in `fork_registry.json`.
8. Decide whether the GitHub-only forks (glow, hermes self-evolution, the Kilo ecosystem, claude-agent-acp) get a use or get archived.

## Adding a card

1. Cite the harness's own README or docs for **Brings**; mark anything else as not measured.
2. List forks from `.gitmodules` and `gh repo list POWERFULMOVES --json name,parent`, with where each is used.
3. Check this registry for the entry, and `quarantine.json`.
4. Check `signing_identity_cards.yaml` and `node-vocabulary.yaml` in PMOVES.AI for identity.
5. Add or update the matching row in `TAC_HARNESS_OVERLAY_MAP.md`.
