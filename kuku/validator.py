"""
Edit-decision validator.

An AI or rules pick looks like:
    {"title": str, "hook": str, "question": str, "why": str,
     "start": int,  "end": int}   ← 1-based cue IDs for the episode

A validated segment:
    {"episode": int, "start_id": int, "end_id": int,
     "start": "MM:SS.cc", "end": "MM:SS.cc", "duration_s": float}

A resolved promo (returned by resolve_ranking):
    {"rank": int, "id": str, "title": str, "hook": str,
     "question": str, "why": str,
     "segments": [segment, ...], "duration_s": float}
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .parser import (
    centiseconds,
    timecode,
    spoken,
    safe_boundary,
    earliest_spoken_after,
    next_spoken_cue,
)

FIELDS = ("title", "hook", "question", "why")
MIN_CS, MAX_CS = 2000, 6000   # 20 s and 60 s in centiseconds


# ── single pick resolver ──────────────────────────────────────────────────────
def _resolve_segments(
    segments_input: List[dict],
    pack: Dict[int, List[dict]],
    label: str = "pick",
) -> tuple[List[dict], int]:
    """
    Validate and resolve a list of segment dicts {episode, start, end}.
    Returns (resolved_list, total_centiseconds).
    """
    if not 1 <= len(segments_input) <= 3:
        raise ValueError(f"{label}: use 1–3 ordered segments.")

    resolved: List[dict] = []
    total = 0
    last_end: Dict[int, int] = {}

    for seg in segments_input:
        ep_s  = seg.get("episode")
        first = seg.get("start")
        last  = seg.get("end")

        if any(type(x) is not int for x in (ep_s, first, last)):
            raise ValueError(f"{label}: episode, start, end must be integers: {seg}")
        if ep_s not in pack:
            raise ValueError(f"{label}: Episode {ep_s} not in the uploaded pack.")

        cues = pack[ep_s]
        n    = len(cues)
        if not (1 <= first <= n and 1 <= last <= n):
            raise ValueError(
                f"{label}: cue range {first}–{last} out of range for "
                f"Episode {ep_s} (1–{n})."
            )

        a = cues[first - 1]["a"]
        b = cues[last  - 1]["b"]

        if a >= b:
            raise ValueError(f"{label}: start ≥ end for segment {seg}.")
        if a < last_end.get(ep_s, 0):
            raise ValueError(f"{label}: overlapping or reversed span in {seg}.")
        if not all(safe_boundary(cues, edge) for edge in (a, b)):
            raise ValueError(
                f"{label}: cut at {timecode(a)}–{timecode(b)} "
                f"splits a spoken line in Episode {ep_s}."
            )

        last_end[ep_s] = b
        resolved.append(
            dict(
                episode=ep_s,
                start_id=first,
                end_id=last,
                start=timecode(a),
                end=timecode(b),
                duration_s=round((b - a) / 100, 2),
            )
        )
        total += b - a

    return resolved, total


def resolve_pick(
    ep: int,
    pick: dict,
    pack: Dict[int, List[dict]],
    segments_override: Optional[List[dict]] = None,
) -> dict:
    """
    Validate a single pick dict for episode *ep* (or use segments_override for
    a montage). Returns a resolved promo dict (without rank/id).
    """
    if not all(isinstance(pick.get(k), str) and pick[k].strip() for k in FIELDS):
        raise ValueError(
            "Every promo needs non-empty strings for title, hook, question, and why."
        )

    segs_in = segments_override or [
        {"episode": ep, "start": pick["start"], "end": pick["end"]}
    ]
    resolved, total = _resolve_segments(segs_in, pack, label=f"E{ep}")

    if not MIN_CS <= total <= MAX_CS:
        raise ValueError(
            f"E{ep}: promo duration {total / 100:.2f}s is outside the 20–60 s window."
        )

    return {**{k: pick[k] for k in FIELDS}, "segments": resolved, "duration_s": total / 100}


# ── episode review collector ──────────────────────────────────────────────────
def collect_picks(
    pack: Dict[int, List[dict]], reviews: List[dict]
) -> Dict[str, dict]:
    """Return {EpisodeKey → resolved_promo} for every non-null pick."""
    ids = [r.get("episode") for r in reviews]
    if any(type(i) is not int for i in ids):
        raise ValueError("Each review must have an integer 'episode' field.")
    if sorted(ids) != sorted(pack.keys()):
        raise ValueError(
            "Reviews must cover each episode in the pack exactly once."
        )
    picks: Dict[str, dict] = {}
    for review in reviews:
        ep   = review["episode"]
        pick = review.get("pick")
        note = review.get("note", "")
        if not isinstance(note, str) or not note.strip():
            raise ValueError(f"Episode {ep}: 'note' must be a non-empty string.")
        if pick is not None:
            picks[f"E{ep}"] = resolve_pick(ep, pick, pack)
    return picks


# ── ranking resolver ──────────────────────────────────────────────────────────
def resolve_ranking(
    pack: Dict[int, List[dict]],
    reviews: List[dict],
    ranking: dict,
) -> List[dict]:
    """
    Validate a ranking dict {order: [...], montage: ...} and return a fully
    resolved, ranked list of promo dicts.
    """
    picks = collect_picks(pack, reviews)

    montage = ranking.get("montage")
    if montage is not None:
        segs = montage.get("segments", [])
        if len(segs) < 2:
            raise ValueError("A montage needs at least two source segments.")

        for seg in segs:
            ep_s   = seg.get("episode")
            parent = picks.get(f"E{ep_s}")
            if parent is None:
                raise ValueError(
                    f"Montage references Episode {ep_s}, which was not nominated."
                )
            # Montage segment must lie inside the nominated window
            orig = parent["segments"][0]
            a_orig = centiseconds(orig["start"])
            b_orig = centiseconds(orig["end"])
            a_seg  = pack[ep_s][seg["start"] - 1]["a"]
            b_seg  = pack[ep_s][seg["end"]   - 1]["b"]
            if a_seg < a_orig or b_seg > b_orig:
                raise ValueError(
                    f"Montage segment in Episode {ep_s} extends outside "
                    f"its nominated window ({orig['start']}–{orig['end']})."
                )

        ep0   = segs[0]["episode"]
        picks["M1"] = resolve_pick(
            ep0,
            {**{k: montage[k] for k in FIELDS}, "start": 0, "end": 0},
            pack,
            segments_override=[
                {"episode": s["episode"], "start": s["start"], "end": s["end"]}
                for s in segs
            ],
        )

    order = ranking.get("order", [])
    if not isinstance(order, list) or set(order) != set(picks) or len(order) != len(picks):
        raise ValueError(
            f"'order' must list each nominated ID exactly once. "
            f"Expected {sorted(picks)}, got {sorted(order)}."
        )

    return [
        dict(rank=i, id=pid, **picks[pid])
        for i, pid in enumerate(order, 1)
    ]


# ── compare endings ───────────────────────────────────────────────────────────
def compare_endings(
    pack: Dict[int, List[dict]], resolved_promo: dict
) -> List[dict]:
    """
    For each segment in *resolved_promo* return a dict with the final cue and
    the earliest spoken line starting at or after the cut time, so editors
    can judge what a later cut reveals.
    """
    out = []
    for seg in resolved_promo["segments"]:
        ep     = seg["episode"]
        end_id = seg["end_id"]
        cues   = pack[ep]
        final  = cues[end_id - 1]
        cut_end_cs = centiseconds(seg["end"]) if isinstance(seg["end"], str) else final["b"]
        nxt    = earliest_spoken_after(cues, cut_end_cs)
        out.append(
            {
                "episode":     ep,
                "seg_start":   seg["start"],
                "seg_end":     seg["end"],
                "final_cue":   final,
                "next_spoken": nxt,
            }
        )
    return out

