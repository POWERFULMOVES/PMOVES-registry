# hyperagint-acp — Provenance (CHIT record)

Human-readable identity-layer narrative for the `hyperagint-acp` registry entry.
The machine-readable source of truth is the `x-pmoves` object in
[agent.json](./agent.json); this file narrates it.

## What this entry is

The **HyPeRAGInT edition** of the PMOVES Hermes Agent MoA harness
(`pmoves-hermes-elder-melchor`), packaged as an ACP stdio agent so any ACP
client (Zed, JetBrains, gemini-cli, fleet harnesses) can spawn it. Built on
PMOVES-registry as base per operator directive (root card `t_f8b3ad71`,
2026-09-26): the PMOVES layer contributes **identity, env/suit selection, and
fleet routing only** — launch mechanics, handshakes, and sanitization are
consumed from the registry's own tooling (`verify_agents.py`, `client.py`,
`registry_utils.py`, `protocol_matrix.py`, `build_registry.py`), never
re-implemented (registry-first doctrine).

## Provenance chain

| Field | Value |
|-------|-------|
| Grounding registry commit | `4b05abb` (branch point of the HyPeRAGInT build; verified ancestor) |
| Entry authored on | `a5cc072` (latest `origin/main` of POWERFULMOVES/PMOVES-registry at authoring time) |
| Branch | `feat/hyperagint-registry-entry` |
| Task | `t_0a9c4bcb` (identity layer; parent root card `t_f8b3ad71`) |
| Authored | 2026-09-27 by pmoves-hermes-elder (EM-FLASH) |
| Harness source | POWERFULMOVES/PMOVES-hermes-agent (public fork, MIT), `acp_adapter/` |
| Version | `0.21.4` = `hermes_cli.__version__` on POWERFULMOVES/PMOVES-hermes-agent `main` (remote; the local sync worktree was stale at 0.21.3) |

Every dispatched call from the harness carries CHIT provenance headers naming
registry commit `4b05abb` (root-card acceptance criterion, preserved through
the routing layer `t_f0e9adf4`).

## MoA preset (EMHERMES)

Seed suit derives from the EMHERMES MoA preset: aggregator and reference both
`zai:glm-5.3-flash`. Per-node variants:

| Node | Mode | Suit |
|------|------|------|
| elder | cloud-first | `suit-elder` |
| z890 | local hermes3 | `suit-z890` |
| 5090 | local hermes3 | `suit-5090` |
| spark | local hermes3 | `suit-spark` |

Suit definitions (env.shared + per-node overlays) live in the **env layer**
(kanban `t_57100539`) and are referenced by name here — deliberately not
duplicated, so the env task stays the single source of truth. Runtime dispatch
resolves node → suit → tailnet serve URL from this entry plus the routing
layer (`t_f0e9adf4`); no hardcoded node tables in harness code. Danger Room
E2E across all four nodes gates rollout (`t_d31ea289`), with operator
(DARKXSIDE) E2E sign-off per the blessed defaults.

## Known gap (tracked, not hidden)

The `windows-x86_64` archive URL targets a GitHub release
(`v0.21.4/hyperagint-acp-windows-x86_64.zip`) that does **not exist yet** —
POWERFULMOVES/PMOVES-hermes-agent has no releases or tags at authoring time.
Cutting that release is proposed as veto-default #5 on the root card
(`t_f8b3ad71`); until it lands, PR CI URL validation, `verify_agents.py`
sandbox launch, and `protocol_matrix.py` for this entry stay red by design.
`sha256` is intentionally omitted until the artifact exists (no fabricated
digests).

## Layout notes

- Entry is fully self-contained in `hyperagint-acp/` (registry convention:
  agent dirs at repo ROOT) to minimize fork-sync merge surface with
  `agentclientprotocol/registry`.
- The distribution is a raw-binary-class zip with `cmd: hyperagint-acp.exe`
  (PyInstaller packaging assumed; `acp_adapter.entry:main` speaks ACP on
  stdio, no args needed). Asset naming matches the hourly `update_versions`
  bot's binary-URL reconstruction; its JSON rewrite path must round-trip the
  `x-pmoves` key — verify when the first bot run touches this entry.
