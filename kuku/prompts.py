"""Prompt templates for the two-pass AI workflow."""
from __future__ import annotations

import json
from typing import Dict, List

from .parser import timecode, centiseconds
from .validator import collect_picks


def _cue_line(c: dict) -> str:
    return f"{c['id']} {timecode(c['a'])}–{timecode(c['b'])} {c['label']} | {c['text']}"


EPISODE_SYSTEM = """\
You are an expert microdrama promo editor making an edit list for viewers new to this show.

Nominate at most ONE continuous 20–60 second cut from these source cues.

Core editorial requirements:
1. Hook (First 3 Seconds): An action, visual reveal, slap, weapon, or arresting spoken line that immediately stops a scrolling viewer.
2. Intelligible Conflict: Establish a clear, stakes-driven conflict that makes sense on its own to someone who has never seen the show.
3. Cliffhanger Ending: Cut at an unresolved climax. This can be:
   - An unanswered spoken question, or
   - A dramatic visual cliffhanger (e.g., an approaching silhouette, an armed guard raising a weapon, an exploding door, a fainting witness, a crucial document catching fire).
4. Inspect the Following Beat: Check the cues immediately after the cut. If the next beat answers the mystery or relieves tension, keep the cut point earlier.
5. Technical Rules:
   - Use only valid cue IDs from the episode.
   - Start at the opening timestamp of your first ID and end at the closing timestamp of your last ID.
   - NEVER cut inside any spoken line. Camera, action, sound, and dialogue cues can overlap.
   - Elapsed play duration must be strictly 20.0 to 60.0 seconds.
6. Honest Pass: If an episode resolves its own tension, lacks an immediate 3-second hook, or cannot meet these criteria, pass (set pick to null) and provide a concrete reason in "note".
7. Story-Specific Rationale: In "why", provide one concrete, story-specific reason why this cut hooks new viewers. Avoid generic boilerplate.

Return ONLY a single JSON object — no markdown, no commentary outside JSON.

Schema:
{
  "episode": <integer>,
  "note":    "<non-empty string explaining decision or pass rationale>",
  "pick": null | {
    "start":    <integer cue id — 1-based>,
    "end":      <integer cue id — 1-based>,
    "title":    "<concise title, up to 9 words>",
    "hook":     "<what the audience sees/hears in the first 3 seconds>",
    "question": "<the specific uncertainty or danger open at the cut point>",
    "why":      "<one story-specific reason to post this promo>"
  }
}"""


RANKING_SYSTEM = """\
You are ranking show promo nominees for a first-time viewer acquisition campaign.

Rank nominees by:
1. Immediate, intelligible hook in the first 3 seconds
2. Single clear, legible conflict for a stranger to the show
3. High-tension unresolved ending (spoken question or visual cliffhanger)
4. Variety across the first five promos (avoid posting near-identical scenes back-to-back)
5. Demote redundant alternatives or cuts requiring deep prior show lore

Optional Montage:
You may optionally add ONE montage (key "montage") joining 2–3 trims from nominated episode windows if combining them improves context or dramatic suspense. Combined play time must be strictly 20.0–60.0 seconds without splitting spoken lines. If included, place "M1" in "order" exactly once.

Return ONLY a single JSON object with no markdown.

Schema:
{
  "order": ["E1", "E12", ...],
  "montage": null | {
    "title":    "<concise title>",
    "hook":     "<first three seconds>",
    "question": "<unresolved question or tension>",
    "why":      "<story-specific rationale>",
    "segments": [
      {"episode": <int>, "start": <cue id>, "end": <cue id>},
      ...
    ]
  }
}"""


def episode_prompt(ep: int, cues: List[dict]) -> str:
    lines = "\n".join(_cue_line(c) for c in cues)
    return f"Episode {ep}\n\n{lines}"


def ranking_prompt(pack: Dict[int, List[dict]], reviews: List[dict]) -> str:
    picks = collect_picks(pack, reviews)
    sections = []
    for pid, pick in picks.items():
        s    = pick["segments"][0]
        a    = centiseconds(s["start"])
        b    = centiseconds(s["end"])
        ep_c = pack[s["episode"]]
        inside = sorted(
            (c for c in ep_c if c["a"] < b and c["b"] > a),
            key=lambda c: (c["a"], c["id"]),
        )
        edge_map = {c["id"]: c for c in (inside[:6] + inside[-6:])}
        cue_block = "\n".join(_cue_line(c) for c in edge_map.values())
        sections.append(f"{pid} {json.dumps(pick, ensure_ascii=False)}\n{cue_block}")
    return "\n\n".join(sections)
