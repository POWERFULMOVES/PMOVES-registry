"""Structural guards for the publish-lane credential gating.

Pins the build-registry.yml wiring that keeps unset repo secrets from
failing the publish lanes at runtime (run 36445441492: empty app-id
rejection; `aws s3 sync --endpoint-url ""` exit 252).
"""

from pathlib import Path

import yaml
from yaml.constructor import SafeConstructor

WORKFLOW = Path(__file__).resolve().parent.parent / "build-registry.yml"

S3_SECRETS = (
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_ENDPOINT",
    "S3_BUCKET",
)
RELEASE_SECRETS = (
    "RELEASE_PLZ_APP_ID",
    "RELEASE_PLZ_APP_PRIVATE_KEY",
)


def load_workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def find_duplicate_keys(text: str) -> list[str]:
    """Return every duplicate mapping key in a YAML document.

    yaml.safe_load silently keeps the LAST duplicate mapping key, so a
    plain parse cannot see them; a second workflow_dispatch under on:
    once broke this workflow at parse time (startup failures, zero step
    logs, all main CI dead). Compose-style loading surfaces every
    duplicate key explicitly.
    """

    class DupeCheck(yaml.SafeLoader):
        pass

    dupes = []

    def construct_mapping(loader, node, deep=False):
        seen = set()
        for key_node, _value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in seen:
                dupes.append(str(key))
            seen.add(key)
        return SafeConstructor.construct_mapping(loader, node, deep=deep)

    DupeCheck.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    yaml.load(text, Loader=DupeCheck)
    return dupes


def test_guard_job_exists_with_both_outputs():
    jobs = load_workflow()["jobs"]
    guard = jobs["publish-credentials"]
    assert guard["outputs"]["s3_configured"] == "${{ steps.guard.outputs.s3_configured }}"
    assert guard["outputs"]["release_configured"] == "${{ steps.guard.outputs.release_configured }}"


def test_guard_step_maps_all_six_secrets_via_env():
    jobs = load_workflow()["jobs"]
    steps = jobs["publish-credentials"]["steps"]
    guard_steps = [s for s in steps if s.get("id") == "guard"]
    assert len(guard_steps) == 1, "exactly one step must carry id: guard"
    env = guard_steps[0]["env"]
    for name in S3_SECRETS + RELEASE_SECRETS:
        assert env[name] == "${{ secrets." + name + " }}"


def test_publish_jobs_need_and_gate_on_the_guard():
    jobs = load_workflow()["jobs"]
    upload = jobs["upload"]
    release = jobs["release"]
    assert "publish-credentials" in upload["needs"]
    assert "publish-credentials" in release["needs"]
    # Each lane must gate on its OWN output: a swap would skip both lanes
    # whenever either credential set is missing.
    assert "needs.publish-credentials.outputs.s3_configured == 'true'" in upload["if"]
    assert "needs.publish-credentials.outputs.release_configured == 'true'" in release["if"]
    # Pre-existing ref/event gating must stay.
    for job in (upload, release):
        assert "github.ref == 'refs/heads/main'" in job["if"]
        assert "always() && !failure() && !cancelled()" in job["if"]


def test_no_job_level_if_reads_secrets_context():
    # `secrets` is not available in job-level if: - GitHub rejects the whole
    # workflow file at parse time (startup failure), so gating must go
    # through the guard job's step outputs.
    jobs = load_workflow()["jobs"]
    for name, job in jobs.items():
        job_if = job.get("if", "")
        assert "secrets." not in job_if, f"{name}: job-level if must not read secrets context"


def test_no_duplicate_yaml_mapping_keys():
    dupes = find_duplicate_keys(WORKFLOW.read_text(encoding="utf-8"))
    assert dupes == [], f"duplicate mapping keys in workflow: {dupes}"


def test_duplicate_key_detector_catches_known_bad():
    # Self-test for the detector above: the exact outage class from
    # t_951e375c (duplicate workflow_dispatch under on:) must be caught.
    bad = "on:\n  workflow_dispatch:\n  workflow_dispatch:\n"
    assert find_duplicate_keys(bad) == ["workflow_dispatch"]
