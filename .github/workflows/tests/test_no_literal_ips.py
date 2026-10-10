"""Registry entries must name hosts, never literal tailnet or private addresses.

This repo is public. A tailnet address (100.64.0.0/10) or an RFC1918 address in an
entry leaks fleet topology and goes stale; the MagicDNS hostname says the same thing
and survives re-addressing. Loopback (127.0.0.0/8) is fine: it is not topology.
"""

import ipaddress
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def _flagged(text: str) -> list[str]:
    hits = []
    for m in IPV4.finditer(text):
        try:
            ip = ipaddress.IPv4Address(m.group())
        except ValueError:
            continue  # e.g. a version string such as 999.1.1.1
        if ip.is_loopback or ip.is_unspecified:
            continue
        if ip.is_private or ip in ipaddress.IPv4Network("100.64.0.0/10"):
            hits.append(m.group())
    return hits


def test_detector_flags_tailnet_and_private_but_not_loopback():
    assert _flagged("host (100.64.0.1, online)") == ["100.64.0.1"]
    assert _flagged("100.127.255.254") == ["100.127.255.254"]
    assert _flagged("lan 192.168.1.5 and 10.0.0.2") == ["192.168.1.5", "10.0.0.2"]
    assert _flagged("OLLAMA_HOST=127.0.0.1:11434") == []
    assert _flagged("100.128.0.1 version 1.2.3.4") == []  # outside CGNAT, public


def test_no_entry_contains_a_literal_tailnet_or_private_ip():
    offenders = {}
    for path in sorted(ROOT.glob("*/agent.json")):
        text = path.read_text(encoding="utf-8")
        json.loads(text)  # a malformed entry is its own failure, not a pass
        hits = _flagged(text)
        if hits:
            offenders[path.parent.name] = len(hits)
    assert not offenders, (
        f"literal tailnet/private IPs in entries (use the MagicDNS hostname): {offenders}"
    )
