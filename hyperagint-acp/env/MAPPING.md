# HyPeRAGInT env layer — EMHERMES preset → per-node suit mapping

Task: t_57100539 (env layer of the HyPeRAGInT harness).
Grounded on POWERFULMOVES/PMOVES-registry @ `4b05abb` (main).

## Source of truth

EMHERMES preset as configured on Hermes profile `pmoves-hermes-elder`
(`config.yaml`, `moa.presets.EMHERMES`):

- aggregator: `zai` / `glm-5.3-flash`
- reference_models: exactly one — `zai` / `glm-5.3-flash`
- degraded_reference_policy: `loud`
- fanout: `per_iteration`
- `moa.max_tokens: 4096` is set at the top-level `moa:` scope, so the preset
  inherits it; it is not preset-specific. It is pinned in env.shared so every
  variant reproduces it.

The top-level `moa:` defaults in that config (ollama-cloud aggregator) belong
to the EMFLASH-style path, not EMHERMES — do not map them into these suits.

## Mapping table

| Env var                                 | EMHERMES preset | z890            | 5090            | spark         | elder         |
|-----------------------------------------|-----------------|-----------------|-----------------|---------------|---------------|
| HYPERAGINT_MOA_PRESET                   | EMHERMES        | EMHERMES        | EMHERMES        | EMHERMES      | EMHERMES      |
| HYPERAGINT_EXECUTION_MODE               | cloud           | local           | local           | local         | cloud         |
| HYPERAGINT_MOA_AGGREGATOR_PROVIDER      | zai             | ollama          | ollama          | ollama        | zai           |
| HYPERAGINT_MOA_AGGREGATOR_MODEL         | glm-5.3-flash   | hermes3:8b      | hermes3:8b      | hermes3:70b   | glm-5.3-flash |
| HYPERAGINT_MOA_REFERENCE_PROVIDER       | zai             | ollama          | ollama          | ollama        | zai           |
| HYPERAGINT_MOA_REFERENCE_MODEL          | glm-5.3-flash   | hermes3:8b      | hermes3:8b      | hermes3:70b   | glm-5.3-flash |
| HYPERAGINT_MOA_REFERENCE_COUNT          | 1               | 1               | 1               | 1             | 1             |
| HYPERAGINT_MOA_DEGRADED_REFERENCE_POLICY| loud            | loud            | loud            | loud          | loud          |
| HYPERAGINT_MOA_FANOUT                   | per_iteration   | per_iteration   | per_iteration   | per_iteration | per_iteration |
| HYPERAGINT_MOA_MAX_TOKENS               | 4096 (inherited)| 4096            | 4096            | 4096          | 4096          |
| HYPERAGINT_NODE                         | —               | z890            | 5090            | spark         | elder         |
| OLLAMA_HOST                             | —               | 127.0.0.1:11434 | 127.0.0.1:11434 | 127.0.0.1:11434 | unset       |

Hardware pins (PMOVES.AI `HERMES.md` fleet table): z890 = RTX 3090 Ti
workstation; 5090 = RTX 5090 32GB primary GPU; spark = DGX GB10 128GB unified
memory (takes hermes3:70b); elder = laptop, GTX 1650 4GB, cloud-only.
Elder is the seed preset with zero model deltas. z890/5090 documented cloud
fallback: zai-coding (same secret as elder). Spark has no documented fallback —
local-only.

## How these vars reach the agent process (ACP handshake)

Registry tooling builds the agent env as:
`distribution.<type>.env` (from `agent.json`) → `sanitize_agent_env()`
(registry_utils.py — DENYLIST) → merged over `AGENT_ENV_PASSTHROUGH` (client.py).

Because the filter is denylist-based, every `HYPERAGINT_*` var and
`OLLAMA_HOST` passes through to the agent at handshake. Never name a suit var
with a reserved name or reserved prefix — `AGENT_ENV_RESERVED_NAMES` /
`AGENT_ENV_RESERVED_PREFIXES` (notably `NODE_`, `NPM_`, `PIP_`, `PYTHON_`,
`UV_`, `XDG_`, `GITHUB_`, `AWS_`) are silently dropped, and process plumbing
(`PATH`, `HOME`, `SystemRoot`, `WINDIR`, `TEMP`/`TMP`) is managed by the
tooling itself, never by suits.

## Secrets (env-indirection doctrine)

No secret values in this directory, ever. Suits reference secret NAMES only
(`ZAI_API_KEY` for the zai cloud path); values resolve per node via the secret
funnel (`pmoves/env.tier-*`). Every node's variant is reproducible from the
registry entry alone precisely because secrets stay outside the registry.

## Provenance policy

`HYPERAGINT_REGISTRY_GROUNDING_COMMIT=4b05abb` records the commit this layer
was authored against. At runtime the routing layer (t_f0e9adf4) must stamp the
LIVE resolved registry commit into `HYPERAGINT_REGISTRY_COMMIT` — the grounding
commit is authoring metadata, not a runtime pin. Dispatched calls carry CHIT
provenance headers naming the live commit.

## Conventions

- Load order: `env.shared` first, then exactly one `suit-<node>.env`
  (overlay wins). `HYPERAGINT_NODE` is the dispatch join key.
- Files are UTF-8 without BOM, LF line endings (Windows quirk per HERMES.md).
- No `${VAR}` expansion literals: values are consumed as plain strings.
- Ports: 11434 = local Ollama; 7700 = Hermes gateway (unrelated to suits).
