"""
Offline keyword-and-question rules baseline — no model, no network.

For each episode, finds the highest-scoring (conflict opener → spoken question)
window that falls within 20–60 seconds. Scores by keyword density.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .parser import spoken, safe_boundary


CONFLICT_RE = re.compile(
    r"\b(?:arrest\w*|betray\w*|blood|burn\w*|dead|death|dying|execut\w*"
    r"|fire|flames?|gallows|gun|hang|kill\w*|lie[ds]?|poison\w*|shackl\w*"
    r"|stole\w*|weapon|wedding)\b",
    re.I,
)
MIN_CS, MAX_CS = 2000, 6000


def _review_episode(ep: int, cues: List[dict]) -> dict:
    # Gather all spoken cues that end on a question at a safe boundary
    endings = [
        c
        for c in cues
        if spoken(c) and "?" in c["text"] and safe_boundary(cues, c["b"])
    ]

    options: List[Tuple] = []
    for opener in cues:
        hits      = len(set(w.lower() for w in CONFLICT_RE.findall(opener["text"])))
        exclaim   = spoken(opener) and "!" in opener["text"]
        if not (hits or exclaim) or not safe_boundary(cues, opener["a"]):
            continue
        for end in endings:
            if end["id"] <= opener["id"]:
                continue
            duration = end["b"] - opener["a"]
            if MIN_CS <= duration <= MAX_CS:
                points = 2 * min(hits, 3) + int(spoken(opener)) + int(exclaim)
                # tie-break: prefer ~32 s, then earlier opener, then later ending
                options.append(
                    (points, -abs(duration - 3200), -opener["id"], -end["id"], opener, end)
                )

    if not options:
        return {
            "episode": ep,
            "pick": None,
            "note": (
                "No eligible conflict-to-question window found "
                "(need a conflict cue followed by a spoken question within 20–60 s)."
            ),
        }

    points, _, _, _, opener, end = max(options, key=lambda row: row[:4])
    hook = opener["text"]
    return {
        "episode": ep,
        "note": (
            f"Rules baseline — {points} signal point(s). "
            "Editorial review recommended before posting."
        ),
        "pick": {
            "start":    opener["id"],
            "end":      end["id"],
            "title":    " ".join(hook.split()[:9]),
            "hook":     hook,
            "question": end["text"],
            "rule_points": points,
            "why": (
                f"Cue {opener['id']} carries a conflict signal; "
                f"the clip ends on the spoken question in cue {end['id']}."
            ),
        },
    }


def rule_run(pack: Dict[int, List[dict]]) -> Tuple[List[dict], dict]:
    """Return (reviews, ranking) from the deterministic offline baseline."""
    reviews = [_review_episode(ep, cues) for ep, cues in pack.items()]
    nominated = sorted(
        (r for r in reviews if r["pick"]),
        key=lambda r: (-r["pick"]["rule_points"], r["episode"]),
    )
    return reviews, {
        "order": [f"E{r['episode']}" for r in nominated],
        "montage": None,
    }

