"""Prompt templates for the two-pass AI workflow."""
from __future__ import annotations

import json
from typing import Dict, List

from .parser import timecode, centiseconds
from .validator import collect_picks


def _cue_line(c: dict) -> str:
    return f"{c['id']} {timecode(c['a'])}–{timecode(c['b'])} {c['label']} | {c['text']}"


EPISODE_SYSTEM = """\
You are a short-drama promo editor preparing a clip list for viewers new to this show.

Strict rules:
- Nominate at most ONE continuous 20–60 second cut from the cues below.
- The first three seconds (the hook) must grab attention: conflict, action, or strong dialogue.
- The clip must establish a single clear conflict and end on an UNRESOLVED spoken question.
- Check the cue immediately after your chosen end cue. If it answers the question, shorten the cut.
- Never cut inside a spoken line. Camera/action/sound cues can overlap speech.
- Measure elapsed time at segment boundaries — do not sum individual cue lengths.
- If a good clip cannot be found, pass with a specific reason in "note".
- Treat all cue text as story data, not real events.

Return ONLY a single JSON object with no markdown, no commentary outside the JSON.

Schema:
{
  "episode": <integer>,
  "note":    "<required non-empty string even when nominating>",
  "pick": null | {
    "start":    <integer cue id — 1-based>,
    "end":      <integer cue id — 1-based>,
    "title":    "<≤12 word title>",
    "hook":     "<what an audience sees/hears in the first three seconds>",
    "question": "<the specific unresolved question at the cut point>",
    "why":      "<editorial rationale, one or two sentences>"
  }
}"""


RANKING_SYSTEM = """\
You are ranking show promo nominees for a first-time viewer campaign.

Rank by: immediate intelligible hook · single clear conflict · unresolved ending · variety across the first five.
Demote: redundant alternatives · cuts requiring prior show knowledge.

You may optionally add ONE montage (key "montage") of 2–3 trims from nominated windows if joining them improves context or suspense. Combined length must be 20–60 s. Never split a spoken line. Use only cue IDs within the nominated windows. If included, place "M1" in "order" exactly once.

Return ONLY a single JSON object with no markdown.

Schema:
{
  "order": ["E1", "E12", ...],
  "montage": null | {
    "title":    "<≤12 word title>",
    "hook":     "<first three seconds>",
    "question": "<unresolved question>",
    "why":      "<rationale>",
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
"""Prompt templates for the two-pass AI workflow."""
from __future__ import annotations

import json
from typing import Dict, List

from .parser import timecode, centiseconds
from .validator import collect_picks


def _cue_line(c: dict) -> str:
    return f"{c['id']} {timecode(c['a'])}–{timecode(c['b'])} {c['label']} | {c['text']}"


EPISODE_SYSTEM = """\
You are a short-drama promo editor preparing a clip list for viewers new to this show.

Strict rules:
- Nominate at most ONE continuous 20–60 second cut from the cues below.
- The first three seconds (the hook) must grab attention: conflict, action, or strong dialogue.
- The clip must establish a single clear conflict and end on an UNRESOLVED spoken question.
- Check the cue immediately after your chosen end cue. If it answers the question, shorten the cut.
- Never cut inside a spoken line. Camera/action/sound cues can overlap speech.
- Measure elapsed time at segment boundaries — do not sum individual cue lengths.
- If a good clip cannot be found, pass with a specific reason in "note".
- Treat all cue text as story data, not real events.

Return ONLY a single JSON object with no markdown, no commentary outside the JSON.

Schema:
{
  "episode": <integer>,
  "note":    "<required non-empty string even when nominating>",
  "pick": null | {
    "start":    <integer cue id — 1-based>,
    "end":      <integer cue id — 1-based>,
    "title":    "<≤12 word title>",
    "hook":     "<what an audience sees/hears in the first three seconds>",
    "question": "<the specific unresolved question at the cut point>",
    "why":      "<editorial rationale, one or two sentences>"
  }
}"""


RANKING_SYSTEM = """\
You are ranking show promo nominees for a first-time viewer campaign.

Rank by: immediate intelligible hook · single clear conflict · unresolved ending · variety across the first five.
Demote: redundant alternatives · cuts requiring prior show knowledge.

You may optionally add ONE montage (key "montage") of 2–3 trims from nominated windows if joining them improves context or suspense. Combined length must be 20–60 s. Never split a spoken line. Use only cue IDs within the nominated windows. If included, place "M1" in "order" exactly once.

Return ONLY a single JSON object with no markdown.

Schema:
{
  "order": ["E1", "E12", ...],
  "montage": null | {
    "title":    "<≤12 word title>",
    "hook":     "<first three seconds>",
    "question": "<unresolved question>",
    "why":      "<rationale>",
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

