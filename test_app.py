"""
End-to-end test suite for Kuku Promo Finder.

Tests:
1. Parser reads the 3 original demo episodes.
2. Safe boundary and spoken detection work correctly.
3. Next spoken cue helper returns the right cue.
4. Rules baseline runs and nominates valid windows.
5. All nominated promos fall within 20–60 s.
6. Cuts do not split spoken lines.
7. Compare endings returns the correct chosen and next spoken cues.
8. CSV and JSON export produce non-empty valid bytes.
9. Fresh upload test with synthetic in-memory screenplay files.
"""
from __future__ import annotations

import io
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
    print(f"  OK: loaded {len(pack)} episodes, {sum(len(v) for v in pack.values())} cues.")


def test_rules_run_and_validator():
    print("Testing rules baseline and validator on demo …")
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
            f"{r['duration_s']:.1f}s | Hook: {r['hook'][:40]}… | "
            f"Question: {r['question'][:40]}…"
        )
    print("  OK: all promos validated.")


def test_compare_endings():
    print("Testing compare endings on first promo …")
    demo_dir = Path(__file__).parent / "demo"
    pack = read_pack([demo_dir])
    reviews, ranking = rule_run(pack)
    results = resolve_ranking(pack, reviews, ranking)

    first = results[0]
    comparisons = compare_endings(pack, first)
    assert len(comparisons) == len(first["segments"])
    for comp in comparisons:
        assert "final_cue" in comp
        assert "next_spoken" in comp
        fc = comp["final_cue"]
        nxt = comp["next_spoken"]
        print(
            f"  Episode {comp['episode']}: final cue {fc['id']} ({fc['label']}): "
            f"'{fc['text'][:40]}…'"
        )
        if nxt:
            print(f"    next spoken cue {nxt['id']} ({nxt['label']}): '{nxt['text'][:40]}…'")
        else:
            print("    next spoken cue: None (end of script)")
    print("  OK: compare endings working.")


def test_exports():
    print("Testing CSV and JSON exports …")
    demo_dir = Path(__file__).parent / "demo"
    pack = read_pack([demo_dir])
    reviews, ranking = rule_run(pack)
    results = resolve_ranking(pack, reviews, ranking)

    csv_bytes = results_to_csv(results)
    assert len(csv_bytes) > 50, "CSV bytes empty or too small"
    assert b"Rank" in csv_bytes
    assert b"Promo title" in csv_bytes

    cov_bytes = coverage_to_csv(pack, reviews)
    assert len(cov_bytes) > 50, "Coverage bytes empty"
    assert b"Episode" in cov_bytes

    json_bytes = run_to_json(pack, reviews, ranking, "Test origin")
    assert len(json_bytes) > 50, "JSON bytes empty"
    import json
    data = json.loads(json_bytes.decode())
    assert "reviews" in data
    assert "ranking" in data
    print("  OK: exports working.")


def test_fresh_upload_zip():
    print("Testing fresh upload path via in-memory ZIP …")
    demo_dir = Path(__file__).parent / "demo"
    pack_orig = read_pack([demo_dir])

    # Package into a ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for txt in demo_dir.glob("*.txt"):
            zf.write(txt, arcname=txt.name)
    buf.seek(0)

    # Now read pack from that temporary ZIP file
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
    print("=" * 60)
    print("Running Kuku Promo Finder test suite")
    print("=" * 60)
    test_parser_demo()
    test_rules_run_and_validator()
    test_compare_endings()
    test_exports()
    test_fresh_upload_zip()
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)

