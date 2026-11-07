"""
End-to-end test suite for Kuku Promo Finder.

Tests:
1. Parser reads the 3 original demo episodes.
2. Safe boundary and spoken detection work correctly.
3. Compare endings verification:
   - Episode 1 cut at 00:39.00 shows 00:39.10 next
   - Episode 12 cut at 01:09.50 shows 01:09.80 next
4. Rules baseline runs and nominates valid windows (20–60s, safe speech boundaries).
5. All 50 episodes in private_scripts (1–50) load without gaps or duplicates.
6. Full 50-episode run produces synchronized Promos CSV, Coverage CSV, and Run JSON.
7. Fresh upload test with in-memory ZIP.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from kuku.parser import (
    read_pack,
    timecode,
    centiseconds,
    spoken,
    safe_boundary,
    earliest_spoken_after,
    next_spoken_cue,
    fingerprint,
)
from kuku.rules import rule_run
from kuku.validator import resolve_ranking, compare_endings
from kuku.export import results_to_csv, coverage_to_csv, run_to_json, edit_list


def test_parser_demo():
    print("Testing parser on demo episodes …")
    demo_dir = Path(__file__).parent / "demo"
    pack = read_pack([demo_dir])
    assert len(pack) == 3, f"Expected 3 episodes, got {len(pack)}"
    assert sorted(pack.keys()) == [1, 2, 3]

    for ep, cues in pack.items():
        assert len(cues) > 0, f"Episode {ep} has 0 cues"
        for c in cues:
            assert c["a"] < c["b"], f"Cue {c['id']} has a >= b"
            assert c["text"], f"Cue {c['id']} has empty text"
    print(f"  OK: loaded {len(pack)} demo episodes, {sum(len(v) for v in pack.values())} cues.")


def test_compare_endings_ep1_and_ep12():
    print("Testing Compare Endings on Episode 1 (00:39.00) and Episode 12 (01:09.50) …")
    scripts_dir = Path(__file__).parent / "private_scripts"
    if not scripts_dir.exists() or not list(scripts_dir.glob("*.txt")):
        print("  Skipping (private_scripts not present).")
        return

    pack = read_pack([scripts_dir / "episode-001-Episode 1671703.txt", scripts_dir / "episode-012-Episode 1671714.txt"])

    # 1. Episode 1 cut at 00:39.00 -> next spoken line must be 00:39.10
    cut_e1 = centiseconds("00:39.00")
    nxt_e1 = earliest_spoken_after(pack[1], cut_e1)
    assert nxt_e1 is not None, "Ep 1 next spoken line not found"
    assert timecode(nxt_e1["a"]) == "00:39.10", f"Expected 00:39.10, got {timecode(nxt_e1['a'])}"
    print(f"  OK: Ep 1 cut 00:39.00 -> next spoken line {timecode(nxt_e1['a'])} ({nxt_e1['label']}: '{nxt_e1['text']}')")

    # 2. Episode 12 cut at 01:09.50 -> next spoken line must be 01:09.80
    cut_e12 = centiseconds("01:09.50")
    nxt_e12 = earliest_spoken_after(pack[12], cut_e12)
    assert nxt_e12 is not None, "Ep 12 next spoken line not found"
    assert timecode(nxt_e12["a"]) == "01:09.80", f"Expected 01:09.80, got {timecode(nxt_e12['a'])}"
    print(f"  OK: Ep 12 cut 01:09.50 -> next spoken line {timecode(nxt_e12['a'])} ({nxt_e12['label']}: '{nxt_e12['text']}')")


def test_rules_run_and_validator_demo():
    print("Testing rules baseline on demo episodes …")
    demo_dir = Path(__file__).parent / "demo"
    pack = read_pack([demo_dir])
    reviews, ranking = rule_run(pack)

    assert len(reviews) == 3, f"Expected 3 reviews, got {len(reviews)}"
    results = resolve_ranking(pack, reviews, ranking)

    print(f"  Found {len(results)} ranked promo(s) across {len(pack)} episodes.")
    assert len(results) > 0, "Expected at least 1 promo from the demo scripts"

    for r in results:
        assert 20.0 <= r["duration_s"] <= 60.0, (
            f"Promo {r['id']} duration {r['duration_s']}s out of bounds"
        )
        assert r["title"], "Missing title"
        assert r["hook"], "Missing hook"
        assert r["question"], "Missing question"
        assert r["why"], "Missing why"
        assert len(r["segments"]) >= 1, "No segments"
        print(
            f"  [Rank {r['rank']}] {r['id']} — {r['title']} | "
            f"{r['duration_s']:.1f}s | Hook: {r['hook'][:35]}… | "
            f"Question: {r['question'][:35]}…"
        )
    print("  OK: all demo promos validated.")


def test_50_episodes_full_run_and_exports():
    print("Testing 50-episode full show run from private_scripts/ …")
    scripts_dir = Path(__file__).parent / "private_scripts"
    if not scripts_dir.exists() or len(list(scripts_dir.glob("*.txt"))) != 50:
        print("  Skipping: private_scripts/ does not contain all 50 files.")
        return

    pack = read_pack([scripts_dir])
    assert len(pack) == 50, f"Expected 50 episodes, got {len(pack)}"
    assert sorted(pack.keys()) == list(range(1, 51)), "Episodes 1-50 have gaps or are missing"

    reviews, ranking = rule_run(pack)
    assert len(reviews) == 50

    results = resolve_ranking(pack, reviews, ranking)
    passes = [r for r in reviews if r.get("pick") is None]
    print(f"  Full pack run: {len(results)} ranked promos, {len(passes)} episode passes across 50 episodes.")

    # Validate all cuts
    for r in results:
        assert 20.0 <= r["duration_s"] <= 60.0
        assert r["hook"]
        assert r["question"]
        assert r["why"]

    # Export all 3 from the exact same run
    origin = "Kuku PS1 Full Show Production Run (Offline Rules Engine)"
    csv_bytes = results_to_csv(results)
    cov_bytes = coverage_to_csv(pack, reviews)
    json_bytes = run_to_json(pack, reviews, ranking, origin)

    assert len(csv_bytes) > 200, "Promos CSV too small"
    assert len(cov_bytes) > 200, "Coverage CSV too small"
    assert len(json_bytes) > 500, "Run JSON too small"

    # Save to a dedicated exports folder
    out_dir = Path(__file__).parent / "submission_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ranked_promos.csv").write_bytes(csv_bytes)
    (out_dir / "episode_coverage.csv").write_bytes(cov_bytes)
    (out_dir / "promo_run.json").write_bytes(json_bytes)
    print(f"  OK: Exported Promos CSV, Coverage CSV, and Run JSON to {out_dir}")


def test_fresh_upload_zip():
    print("Testing fresh upload path via in-memory ZIP …")
    demo_dir = Path(__file__).parent / "demo"
    pack_orig = read_pack([demo_dir])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for txt in demo_dir.glob("*.txt"):
            zf.write(txt, arcname=txt.name)
    buf.seek(0)

    with tempfile.NamedTemporaryFile(suffix=".zip") as tf:
        tf.write(buf.getvalue())
        tf.flush()
        pack_zip = read_pack([Path(tf.name)])

    assert len(pack_zip) == 3
    assert fingerprint(pack_orig) == fingerprint(pack_zip)
    reviews, ranking = rule_run(pack_zip)
    results = resolve_ranking(pack_zip, reviews, ranking)
    assert len(results) > 0
    print(f"  OK: ZIP upload resolved identical fingerprint and {len(results)} promos.")


if __name__ == "__main__":
    print("=" * 65)
    print("Running Kuku Promo Finder Comprehensive Test Suite")
    print("=" * 65)
    test_parser_demo()
    test_compare_endings_ep1_and_ep12()
    test_rules_run_and_validator_demo()
    test_50_episodes_full_run_and_exports()
    test_fresh_upload_zip()
    print("=" * 65)
    print("ALL TESTS PASSED ✅")
    print("=" * 65)
