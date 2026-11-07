"""
Editorial Rules Engine — deterministic microdrama candidate extraction & ranking.

Evaluates:
1. Opening 3-second retention hook (action, conflict dialogue, exclamations)
2. Standalone story clarity for a new viewer
3. Unresolved cliffhanger ending (spoken questions AND visual cliffhangers)
4. Safe boundary verification (never cutting mid-speech)
5. Story-specific editorial rationales
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .parser import spoken, safe_boundary, timecode


CONFLICT_RE = re.compile(
    r"\b(?:arrest\w*|betray\w*|blood\w*|burn\w*|dead|death|dying|execut\w*"
    r"|fire|flames?|gallows|gun\w*|hang\w*|kill\w*|lie[ds]?|poison\w*|shackl\w*"
    r"|stole\w*|thief|weapon\w*|wedding\w*|whip\w*|wound\w*|danger|traitor\w*)\b",
    re.I,
)

VISUAL_CLIFFHANGER_RE = re.compile(
    r"\b(?:door\w*|knock\w*|smoke|fire|flame\w*|gun\w*|weapon|blade|sword|club\w*"
    r"|shackl\w*|chain\w*|hand\w*|collapse\w*|faint\w*|poison\w*|arrest\w*"
    r"|gallows|hang\w*|whip\w*|blood\w*|fingerprint\w*|lock\w*|latch\w*"
    r"|footstep\w*|shadow\w*|silhouette\w*|burn\w*|explod\w*|blast\w*)\b",
    re.I,
)

MIN_CS, MAX_CS = 2000, 6000


def _story_specific_why(opener: dict, end: dict, is_question: bool) -> str:
    """Generate a story-specific reason why this cut works for a new viewer."""
    op_speaker = opener["label"] if spoken(opener) else "Opening visual"
    end_speaker = end["label"] if spoken(end) else "Closing visual"

    if is_question:
        return (
            f"Starts immediately with {op_speaker}'s conflict hook in the first 3 seconds. "
            f"The cut terminates on {end_speaker}'s spoken question ({timecode(end['b'])}) "
            f"to force a new viewer to seek the answer in the next episode."
        )
    return (
        f"Delivers an immediate hook through {op_speaker} inside 3 seconds. "
        f"Ends on a visual cliffhanger beat ({end['text'][:65]}...) at {timecode(end['b'])}, "
        f"cutting away before the physical consequence or identity is revealed."
    )


def _review_episode(ep: int, cues: List[dict]) -> dict:
    # 1. Identify all eligible endings that end at a safe boundary
    # Endings can be spoken questions OR high-stakes visual cliffhangers
    endings = []
    for c in cues:
        if not safe_boundary(cues, c["b"]):
            continue
        if spoken(c) and "?" in c["text"]:
            endings.append((c, True))  # (cue, is_spoken_question)
        elif not spoken(c) and VISUAL_CLIFFHANGER_RE.search(c["text"]):
            endings.append((c, False))  # (cue, is_visual_cliffhanger)

    options: List[Tuple] = []

    for opener in cues:
        if not safe_boundary(cues, opener["a"]):
            continue

        # Check 3-second hook window [opener['a'], opener['a'] + 300]
        hook_cues = [c for c in cues if opener["a"] <= c["a"] < opener["a"] + 300]
        hook_text = " ".join(c["text"] for c in hook_cues) if hook_cues else opener["text"]

        hits_3s = len(set(w.lower() for w in CONFLICT_RE.findall(hook_text)))
        is_exclaim_3s = any(spoken(c) and "!" in c["text"] for c in hook_cues) or "!" in opener["text"]

        if not (hits_3s or is_exclaim_3s or spoken(opener)):
            continue

        for end, is_q in endings:
            if end["id"] <= opener["id"]:
                continue
            duration = end["b"] - opener["a"]
            if MIN_CS <= duration <= MAX_CS:
                # Score components:
                # 1. Hook velocity in first 3 seconds (up to 6 pts)
                hook_score = 3 * min(hits_3s, 2) + (2 if is_exclaim_3s else 0)
                # 2. Overall conflict clarity across window
                win_text = " ".join(c["text"] for c in cues[opener["id"] - 1 : end["id"]])
                total_hits = len(set(w.lower() for w in CONFLICT_RE.findall(win_text)))
                clarity_score = 2 * min(total_hits, 4)
                # 3. Unresolved ending strength (spoken question prioritized over visual cliffhanger)
                ending_score = 4 if is_q else 2
                # 4. Preferred duration window (25s–42s is sweet spot for reels)
                pacing_score = -abs(duration - 3200) // 200

                total_points = hook_score + clarity_score + ending_score
                options.append(
                    (total_points, pacing_score, -opener["id"], -end["id"], opener, end, is_q)
                )

    if not options:
        return {
            "episode": ep,
            "pick": None,
            "note": (
                "No eligible 20–60s window met hook and unresolved cliffhanger requirements."
            ),
        }

    points, _, _, _, opener, end, is_q = max(options, key=lambda row: (row[0], row[1], row[2], row[3]))
    hook = opener["text"]
    question = end["text"] if is_q else f"[Visual Cliffhanger] {end['text']}"
    title_words = opener["text"].split()[:9]
    title = " ".join(title_words).strip('"\',.:;- ')

    return {
        "episode": ep,
        "note": f"Nominated for show slate ({points} signal points; {'Spoken Question' if is_q else 'Visual Cliffhanger'}).",
        "pick": {
            "start": opener["id"],
            "end": end["id"],
            "title": title if title else f"Episode {ep} Conflict",
            "hook": hook,
            "question": question,
            "rule_points": points,
            "why": _story_specific_why(opener, end, is_q),
        },
    }


def rule_run(pack: Dict[int, List[dict]]) -> Tuple[List[dict], dict]:
    """Return (reviews, ranking) from the deterministic editorial rules engine."""
    reviews = [_review_episode(ep, cues) for ep, cues in pack.items()]
    nominated = sorted(
        (r for r in reviews if r["pick"]),
        key=lambda r: (-r["pick"]["rule_points"], r["episode"]),
    )
    return reviews, {
        "order": [f"E{r['episode']}" for r in nominated],
        "montage": None,
    }
