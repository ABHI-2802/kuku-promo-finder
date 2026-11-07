"""CSV / JSON export helpers."""
from __future__ import annotations

import csv
import io
import json
from typing import Dict, List


def edit_list(segments: List[dict]) -> str:
    return " then ".join(
        f"E{s['episode']} {s['start']}–{s['end']}" for s in segments
    )


def results_to_csv(results: List[dict]) -> bytes:
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow([
        "Rank", "ID", "Promo title",
        "Segments in playback order", "Total seconds",
        "First three seconds (hook)", "Unanswered question", "Why it works",
    ])
    for r in results:
        w.writerow([
            r["rank"], r["id"], r["title"],
            edit_list(r["segments"]),
            f"{r['duration_s']:.2f}",
            r["hook"], r["question"], r["why"],
        ])
    return buf.getvalue().encode("utf-8-sig")


def coverage_to_csv(pack: Dict[int, List[dict]], reviews: List[dict]) -> bytes:
    buf    = io.StringIO()
    w      = csv.writer(buf)
    ep_map = {r["episode"]: r for r in reviews}
    w.writerow(["Episode", "Cues", "Decision", "Candidate title", "Review note"])
    for ep in sorted(pack):
        r = ep_map.get(ep, {})
        w.writerow([
            ep,
            len(pack[ep]),
            "Nominate" if r.get("pick") else "Pass",
            r["pick"]["title"] if r.get("pick") else "",
            r.get("note", ""),
        ])
    return buf.getvalue().encode("utf-8-sig")


def run_to_json(
    pack,
    reviews: List[dict],
    ranking: dict,
    origin: str,
) -> bytes:
    from .parser import fingerprint
    data = {
        "origin": origin,
        "pack_sha256": fingerprint(pack),
        "reviews": reviews,
        "ranking": ranking,
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
