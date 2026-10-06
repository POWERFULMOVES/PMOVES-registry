#!/usr/bin/env python3
"""HyPeRAGInT routing layer - registry-driven dispatch.

Resolves node -> suit -> tailnet URL, the fallback graph, and provenance
headers ENTIRELY from the `x-pmoves` block of hyperagint-acp/agent.json at
runtime. No node, suit, URL, or header tables live in this file; this script
only interprets the entry. Harness-consumed glue (PMOVES routing layer), not
registry infrastructure - it imports nothing from .github/workflows.

Stdlib only: json / os / sys / socket / urllib / http.server.

Commands:
  resolve                 Print the four-node resolution table (dry-run dispatch).
  probe --node NAME       POST a probe along the node's fallback chain, carrying
                          provenance headers; loud-fails when every hop is
                          unreachable (exit 3).
  echo-verify             Prove header construction against a local echo server
                          on 127.0.0.1 (wire-format proof, not tailnet transit).

Provenance doctrine (env.shared + root card, resolved structurally):
  HYPERAGINT_REGISTRY_COMMIT           = live-resolved registry commit (runtime stamp)
  HYPERAGINT_REGISTRY_GROUNDING_COMMIT = authoring grounding commit from the entry
"""

import argparse
import json
import os
import socket
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROUTING_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROUTING_DIR.parents[1]
ENTRY_PATH = REPO_ROOT / "hyperagint-acp" / "agent.json"


# ---------------------------------------------------------------- entry load

def load_entry():
    with open(ENTRY_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def live_registry_commit():
    """Resolve the LIVE registry commit from .git without subprocess/git.

    Reads .git/HEAD, then the loose ref; falls back to packed-refs. Returns
    None when unresolvable (detached/absent) - callers must surface that
    loudly rather than inventing a value.
    """
    git = REPO_ROOT / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if head.startswith("ref: "):
        ref = head[5:]
        loose = git / ref
        try:
            return loose.read_text(encoding="utf-8").strip() or None
        except OSError:
            pass
        try:
            for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
                if line.strip().endswith(" " + ref):
                    return line.split()[0]
        except OSError:
            pass
        return None
    return head or None


def suit_env(xp, suit_name):
    """env.shared base overlaid by the named suit (registry-embedded copies)."""
    merged = dict(xp.get("env_shared", {}).get("vars", {}))
    merged.update(xp.get("suits", {}).get(suit_name, {}).get("vars", {}))
    return merged


def provenance_headers(xp):
    """Substitute routing.headers tokens: {live_registry_commit}, {grounding_commit}."""
    live = live_registry_commit()
    grounding = xp.get("provenance", {}).get("registry_commit")
    tokens = {
        "{live_registry_commit}": live,
        "{grounding_commit}": grounding,
    }
    headers = {}
    problems = []
    for name, template in xp.get("routing", {}).get("headers", {}).items():
        value = template
        for token, resolved in tokens.items():
            value = value.replace(token, resolved or "")
        if not value or "{" in value:
            problems.append("%s -> %r (live=%s)" % (name, template, live))
        headers[name] = value
    return headers, problems


def stamp_env(xp, node_name):
    """Env block a real dispatch would hand the node-side harness."""
    node = node_entry(xp, node_name)
    env = suit_env(xp, node["suit"])
    env["HYPERAGINT_REGISTRY_GROUNDING_COMMIT"] = xp["provenance"]["registry_commit"]
    live = live_registry_commit()
    if live:
        env["HYPERAGINT_REGISTRY_COMMIT"] = live
    return env


def node_entry(xp, name):
    for n in xp.get("nodes", []):
        if n["node"] == name:
            return n
    raise KeyError("node %r not in registry entry x-pmoves.nodes" % name)


def fallback_chain(xp, name):
    routing = xp.get("routing", {})
    return list(routing.get("fallbacks", {}).get(name, []))


# ------------------------------------------------------------------ commands

def cmd_resolve(xp, as_json):
    live = live_registry_commit()
    rows = []
    for n in xp.get("nodes", []):
        rows.append({
            "node": n["node"],
            "mode": n.get("mode"),
            "suit": n["suit"],
            "url": n.get("url"),
            "url_verified": n.get("url_verified", False),
            "fallbacks": fallback_chain(xp, n["node"]),
            "suit_vars": len(suit_env(xp, n["suit"])),
        })
    out = {
        "harness": xp.get("harness", {}).get("kind"),
        "live_registry_commit": live,
        "grounding_commit": xp.get("provenance", {}).get("registry_commit"),
        "source": str(ENTRY_PATH),
        "nodes": rows,
    }
    if as_json:
        print(json.dumps(out, indent=2))
        return 0
    print("HyPeRAGInT dispatch resolution (dry-run) - source: %s" % ENTRY_PATH)
    print("live registry commit : %s" % (live or "UNRESOLVED (loud, by design)"))
    print("grounding commit     : %s" % out["grounding_commit"])
    print()
    for r in rows:
        mark = "verified" if r["url_verified"] else "UNVERIFIED"
        print("node %-6s mode=%-12s suit=%-10s url=%s [%s]" % (
            r["node"], r["mode"], r["suit"], r["url"], mark))
        print("       fallbacks=%s suit_vars=%d" % (r["fallbacks"] or "[] (loud fail)", r["suit_vars"]))
    unresolved = [r["node"] for r in rows if not r["url_verified"]]
    if unresolved:
        print()
        print("NOTE: %s URL(s) unverified at authoring (tailscale down); owner: t_c368f165" % ",".join(unresolved))
    if not live:
        print("NOTE: live registry commit unresolved - dispatch would loud-fail provenance stamping")
    return 0


def send_probe(url, headers, payload, timeout):
    """POST the probe. Returns (status_or_None, detail, body_bytes).

    status None = unreachable (no HTTP response at all). Any HTTP response
    proves the route is up end to end; the caller decides whether the status
    counts as healthy (the fallback walker advances past 5xx).
    """
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, "http %s from %s" % (resp.status, url), resp.read()
    except urllib.error.HTTPError as e:
        # Any HTTP response (even 4xx/5xx) proves the route is UP end to end.
        return e.code, "http %s (route up, endpoint answered) %s" % (e.code, url), e.read()
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        return None, "unreachable %s (%s)" % (url, e.__class__.__name__), None


def cmd_probe(xp, node_name, timeout):
    headers, problems = provenance_headers(xp)
    if problems:
        for p in problems:
            print("PROVENANCE ERROR: %s" % p, file=sys.stderr)
        return 4
    env = stamp_env(xp, node_name)
    print("env stamp for dispatch to %s:" % node_name)
    for key in sorted(env):
        print("  %s=%s" % (key, env[key]))
    print()
    chain = [node_name] + [n for n in fallback_chain(xp, node_name) if n != node_name]
    trace = []
    for hop in chain:
        hop_node = node_entry(xp, hop)
        url = hop_node.get("url")
        if not url:
            trace.append("  %s: no url in entry -> skip" % hop)
            continue
        status, detail, _body = send_probe(
            url, headers, {"probe": "hyperagint-routing", "node": node_name}, timeout)
        if status and status >= 500:
            trace.append("  %s: degraded - %s (route up, service error; trying next hop)" % (hop, detail))
            continue
        mark = "REACHABLE" if status else "down"
        trace.append("  %s: %s - %s" % (hop, mark, detail))
        if status:
            print("\n".join(trace))
            print("dispatch route resolved via %s" % hop)
            return 0
    print("\n".join(trace))
    print("ALL HOPS UNREACHABLE - loud failure per HYPERAGINT_MOA_DEGRADED_REFERENCE_POLICY=loud", file=sys.stderr)
    return 3


class _Echo(BaseHTTPRequestHandler):
    def do_POST(self):
        # urllib capitalizes stored header names, so the wire form is
        # "X-hyperagint-registry-commit" (RFC 9110: case-insensitive). Match
        # by case-insensitive substring - never by prefix or exact case.
        received = {k: v for k, v in self.headers.items() if "hyperagint" in k.lower()}
        body = json.dumps({"received_headers": received}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def cmd_echo_verify(xp, port):
    server = HTTPServer(("127.0.0.1", port), _Echo)
    bound = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        headers, problems = provenance_headers(xp)
        if problems:
            for p in problems:
                print("PROVENANCE ERROR: %s" % p, file=sys.stderr)
            return 4
        status, detail, body = send_probe(
            "http://127.0.0.1:%d/" % bound, headers,
            {"probe": "header-construction-proof"}, timeout=5)
        print("LOCAL HEADER-CONSTRUCTION PROOF (echo server on 127.0.0.1:%d - not tailnet transit)" % bound)
        print("probe result: %s" % detail)
        if status != 200 or body is None:
            print("VERDICT: FAIL - echo server did not answer cleanly", file=sys.stderr)
            return 4
        expected = {k.lower(): v for k, v in headers.items()}
        received = {k.lower(): v for k, v in
                    json.loads(body.decode("utf-8")).get("received_headers", {}).items()}
        print("closed-loop check (entry policy vs headers received on the wire):")
        ok = True
        for name in sorted(expected):
            got = received.get(name)
            match = got == expected[name]
            ok = ok and match
            print("  %s:" % name)
            print("    expected: %s" % expected[name])
            print("    received: %s [%s]" % (got, "match" if match else "MISMATCH"))
        print("VERDICT: %s" % (
            "provenance headers verified on the wire (echo round-trip)" if ok
            else "FAIL - wire headers do not match entry policy"))
        return 0 if ok else 4
    finally:
        server.shutdown()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["resolve", "probe", "echo-verify"])
    ap.add_argument("--node")
    ap.add_argument("--timeout", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args(argv)
    xp = load_entry().get("x-pmoves", {})
    if args.command == "resolve":
        return cmd_resolve(xp, args.json)
    if args.command == "probe":
        if not args.node:
            ap.error("probe requires --node")
        return cmd_probe(xp, args.node, args.timeout)
    if args.command == "echo-verify":
        return cmd_echo_verify(xp, args.port)
    return 2


if __name__ == "__main__":
    sys.exit(main())
