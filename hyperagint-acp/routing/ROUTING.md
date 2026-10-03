# HyPeRAGInT routing layer

Registry-driven dispatch for the HyPeRAGInT harness (PMOVES layer: identity,
env/suit selection, fleet routing — consumes the registry harness, never
re-implements it).

## Source of truth

Everything the dispatcher does is read at runtime from the `x-pmoves` block of
`../agent.json`: `nodes[]` (node → suit + tailnet URL), `suits` + `env_shared`
(embedded verbatim from `../env/`, content owned by kanban t_57100539 /
commit a3f9c9c), `routing.headers`, `routing.fallbacks`, and
`provenance.registry_commit`. No node, suit, URL, or header table exists in
`dispatch.py` — it only interprets the entry.

## Commands

    python dispatch.py resolve              # dry-run: resolve all nodes (table)
    python dispatch.py resolve --json       # same, machine-readable
    python dispatch.py probe --node z890    # walk the fallback chain with provenance headers
    python dispatch.py echo-verify          # prove header wire format on 127.0.0.1

Exit codes: 0 resolved/reached, 3 all hops unreachable (loud), 4 provenance
construction failure (never dispatch with unresolved provenance).

## Per-node standup (one line per node, on the node)

    tailscale serve --bg 7700

This fronts the node's Hermes gateway (fleet port 7700 per PMOVES.AI
HERMES.md) at `https://<node>.<tailnet>.ts.net/`. Node URLs and their
verification status live in the entry (`nodes[].url`, `nodes[].url_verified`,
`nodes[].url_basis`).

## Provenance doctrine (dual header)

    X-Hyperagint-Registry-Commit:           <live-resolved registry commit, stamped at runtime>
    X-Hyperagint-Registry-Grounding-Commit: 4b05abb (authoring anchor, from the entry)

The live commit names the checkout the dispatch actually resolved against; the
grounding commit is permanent authoring provenance. Resolving the root-card
"4b05abb on every call" doctrine and the env.shared "live commit at runtime"
doctrine: both ride every call, neither overrides the other.

## Fallback doctrine

Chains are declared per node in `routing.fallbacks` (z890→elder, 5090→elder,
elder→[], spark→[]). First reachable hop wins; an empty chain fails loud —
spark is local-only by suit doctrine and never silently reroutes. Every hop is
attempted with full provenance headers.

## Gates owned elsewhere

- `url_verified` flips: kanban t_c368f165 (validation) once the tailnet is
  reachable from a verification context.
- End-to-end dispatch to real agent launches: gated on the v0.21.4 release
  artifact (veto-default #5 on t_f8b3ad71) + Danger Room E2E (t_d31ea289).
- Registry verify/client/protocol tooling: PMOVES-registry's own; untouched.
