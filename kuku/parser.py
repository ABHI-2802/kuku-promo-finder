"""
Screenplay parser — reads timestamped .txt files, directories, or ZIPs.

Expected format per file:
    EPISODE NUMBER: Episode <N>

    **SPEAKER / TYPE:**
    Start: (MM:SS.cc) | End: (MM:SS.cc)
    Cue text here.

Non-speech types (CAMERA, ACTION, SOUND FX, …) receive IDs and are
included in the cue list; they just don't qualify as spoken lines.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional


# ── regexes ──────────────────────────────────────────────────────────────────
EPISODE_RE = re.compile(
    r"^EPISODE NUMBER:[ \t]*(?:Episode[ \t]+)?(\d+)\b", re.I | re.M
)
STAMP = r"\d+:[0-5]\d(?:\.\d{1,2})?"
BLOCK_RE = re.compile(
    r"^[ \t]*\*\*([^\n]+?)\*\*[ \t]*\n"
    r"[ \t]*Start:[ \t]*\((" + STAMP + r")\)[ \t]*\|[ \t]*End:[ \t]*\(("
    + STAMP
    + r")\)[ \t]*\n"
    r"(.*?)(?=\n[ \t]*\n|\n[ \t]*(?:\*\*|SCENE \d|--- SCRIPT)|\Z)",
    re.M | re.S,
)
NONSPEECH = {"CAMERA", "ACTION", "SOUND FX", "SFX", "MUSIC", "TRANSITION", "VFX"}


# ── time helpers ──────────────────────────────────────────────────────────────
def centiseconds(stamp: str) -> int:
    """Convert MM:SS.cc string to centiseconds integer."""
    minutes, rest = stamp.split(":", 1)
    whole, _, frac = rest.partition(".")
    return (60 * int(minutes) + int(whole)) * 100 + int((frac + "00")[:2])


def timecode(value: int) -> str:
    """Convert centiseconds integer to MM:SS.cc string."""
    mins, rem = divmod(value, 6000)
    secs, cs = divmod(rem, 100)
    return f"{mins:02d}:{secs:02d}.{cs:02d}"


# ── cue helpers ───────────────────────────────────────────────────────────────
def spoken(cue: dict) -> bool:
    return cue["label"] not in NONSPEECH


def safe_boundary(cues: List[dict], point: int) -> bool:
    """True if *point* does not land mid-speech (a < point < b) in any spoken cue."""
    return not any(c["a"] < point < c["b"] for c in cues if spoken(c))


def earliest_spoken_after(cues: List[dict], cut_end_cs: int) -> Optional[dict]:
    """
    Return the earliest spoken line starting at or after the cut time (c['a'] >= cut_end_cs).
    """
    candidates = [c for c in cues if spoken(c) and c["a"] >= cut_end_cs]
    if not candidates:
        return None
    return min(candidates, key=lambda c: (c["a"], c["id"]))


def next_spoken_cue(cues: List[dict], after_id: int) -> Optional[dict]:
    """Legacy helper: return earliest spoken cue starting after cue after_id's end."""
    if 1 <= after_id <= len(cues):
        return earliest_spoken_after(cues, cues[after_id - 1]["b"])
    return None


# ── single-file parser ────────────────────────────────────────────────────────
def _parse_file(name: str, raw: bytes) -> tuple[int, List[dict]]:
    source = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    heading = EPISODE_RE.search(source)
    if not heading:
        if "Start: (" in source:
            raise ValueError(f"{name}: has timed cues but no EPISODE NUMBER header.")
        return -1, []  # skip files with no episode header

    number = int(heading.group(1))
    cues: List[dict] = []
    for i, (tag, start, end, body) in enumerate(BLOCK_RE.findall(source), 1):
        label = tag.split("(")[0].strip(" :").upper()
        cue = dict(
            id=i,
            a=centiseconds(start),
            b=centiseconds(end),
            label=label,
            text=" ".join(body.split()).strip('"""'),
        )
        if cue["a"] >= cue["b"]:
            raise ValueError(f"{name}: cue {i} has start ≥ end.")
        if not cue["text"]:
            raise ValueError(f"{name}: cue {i} has empty text.")
        cues.append(cue)

    declared = len(re.findall(r"^[ \t]*Start:[ \t]*\(", source, re.M))
    if not cues or len(cues) != declared:
        raise ValueError(
            f"{name}: parsed {len(cues)} cues but found {declared} Start: markers."
        )
    return number, cues


# ── pack reader ───────────────────────────────────────────────────────────────
def read_pack(paths: List[Path]) -> Dict[int, List[dict]]:
    """Read one or more paths (files, dirs, zips) → {episode_number: [cues]}."""
    episodes: Dict[int, List[dict]] = {}

    def _add(name: str, data: bytes) -> None:
        number, cues = _parse_file(name, data)
        if number == -1:
            return
        if number in episodes:
            raise ValueError(
                f"Two files both declare Episode {number}. Keep only one copy."
            )
        episodes[number] = cues

    for path in paths:
        path = Path(path)
        if path.is_dir():
            for item in sorted(path.rglob("*")):
                if (
                    item.is_file()
                    and item.suffix.lower() == ".txt"
                    and "__MACOSX" not in item.parts
                    and not item.name.startswith(".")
                ):
                    _add(item.name, item.read_bytes())
        elif path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as arc:
                for info in arc.infolist():
                    mem = Path(info.filename)
                    if (
                        mem.suffix.lower() == ".txt"
                        and "__MACOSX" not in mem.parts
                        and not mem.name.startswith(".")
                    ):
                        _add(info.filename, arc.read(info))
        else:
            _add(path.name, path.read_bytes())

    if not episodes:
        raise ValueError(
            "No valid episodes found. Each .txt file needs an EPISODE NUMBER header."
        )
    return dict(sorted(episodes.items()))


def fingerprint(pack: Dict[int, List[dict]]) -> str:
    content = json.dumps(list(pack.items()), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()

