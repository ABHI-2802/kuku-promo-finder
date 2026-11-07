"""
AI client — chat-completions-compatible endpoint wrapper.

Caches valid responses to disk so identical (url, model, prompt) calls are
free on retry. Invalid or stale cached responses are evicted automatically.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Callable, Dict, List
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def _decode(text: str) -> dict:
    """Strip optional markdown fences and parse JSON."""
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, re.S | re.I)
    return json.loads(fenced.group(1) if fenced else text)


def _cache_key(url: str, model: str, system: str, prompt: str) -> str:
    raw = json.dumps([url, model, system, prompt], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def call_model(
    prompt: str,
    system: str,
    url: str,
    model: str,
    api_key: str,
    cache_dir: Path,
    step: str,
    validate: Callable[[dict], None],
    timeout: int = 180,
) -> dict:
    """
    POST to a chat-completions endpoint and cache the validated response.
    Re-uses a cached file on the same (url, model, system, prompt); evicts
    the cache if the response no longer passes the validator.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    key  = _cache_key(url, model, system, prompt)
    path = cache_dir / f"{step}-{key}.json"

    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate(value)
            return value
        except Exception:
            path.unlink(missing_ok=True)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        }
    ).encode()

    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=timeout) as resp:
            content = json.load(resp)["choices"][0]["message"]["content"]
    except HTTPError as e:
        raise ValueError(
            f"HTTP {e.code} from the model endpoint at step '{step}'. "
            f"Check your API key, endpoint URL, and model name."
        ) from e
    except URLError as e:
        raise ValueError(
            f"Could not reach the model endpoint at step '{step}': {e.reason}"
        ) from e

    # Write to temp file first to avoid partial writes on failure
    fd, tmp_path = tempfile.mkstemp(
        dir=cache_dir, prefix=f"{step}-attempt-", suffix=".txt"
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
        value = _decode(content)
        validate(value)
    except Exception as exc:
        raise ValueError(
            f"Model response failed validation at step '{step}'. "
            f"Raw reply saved to {tmp_path}. Error: {exc}"
        ) from exc

    # Promote temp file to canonical cache path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return value


def run_api(
    pack: Dict[int, List[dict]],
    url: str,
    model: str,
    api_key: str,
    cache_dir: Path,
    progress_cb: Callable[[str, float], None] | None = None,
) -> tuple[List[dict], dict]:
    """
    Full two-pass AI run.

    progress_cb(message, fraction_0_to_1) is called at each episode and before
    the ranking pass, so the UI can display a progress bar.

    Returns (reviews, ranking).
    """
    from .prompts import episode_prompt, ranking_prompt, EPISODE_SYSTEM, RANKING_SYSTEM
    from .validator import collect_picks

    n_eps    = len(pack)
    reviews: List[dict] = []

    for i, (ep, cues) in enumerate(pack.items()):
        if progress_cb:
            progress_cb(f"Analysing Episode {ep} …", i / (n_eps + 1))

        def _ep_validate(v, ep=ep, cues=cues):
            collect_picks({ep: cues}, [v])

        review = call_model(
            prompt=episode_prompt(ep, cues),
            system=EPISODE_SYSTEM,
            url=url,
            model=model,
            api_key=api_key,
            cache_dir=cache_dir,
            step=f"ep-{ep:03d}",
            validate=_ep_validate,
        )
        reviews.append(review)

    if not any(r["pick"] for r in reviews):
        return reviews, {"order": [], "montage": None}

    if progress_cb:
        progress_cb("Ranking nominations …", n_eps / (n_eps + 1))

    from .validator import resolve_ranking as _rr

    def _rank_validate(v):
        _rr(pack, reviews, v)

    ranking = call_model(
        prompt=ranking_prompt(pack, reviews),
        system=RANKING_SYSTEM,
        url=url,
        model=model,
        api_key=api_key,
        cache_dir=cache_dir,
        step="ranking",
        validate=_rank_validate,
    )
    return reviews, ranking
"""
AI client — chat-completions-compatible endpoint wrapper.

Caches valid responses to disk so identical (url, model, prompt) calls are
free on retry. Invalid or stale cached responses are evicted automatically.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Callable, Dict, List
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def _decode(text: str) -> dict:
    """Strip optional markdown fences and parse JSON."""
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, re.S | re.I)
    return json.loads(fenced.group(1) if fenced else text)


def _cache_key(url: str, model: str, system: str, prompt: str) -> str:
    raw = json.dumps([url, model, system, prompt], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def call_model(
    prompt: str,
    system: str,
    url: str,
    model: str,
    api_key: str,
    cache_dir: Path,
    step: str,
    validate: Callable[[dict], None],
    timeout: int = 180,
) -> dict:
    """
    POST to a chat-completions endpoint and cache the validated response.
    Re-uses a cached file on the same (url, model, system, prompt); evicts
    the cache if the response no longer passes the validator.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    key  = _cache_key(url, model, system, prompt)
    path = cache_dir / f"{step}-{key}.json"

    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate(value)
            return value
        except Exception:
            path.unlink(missing_ok=True)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        }
    ).encode()

    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=timeout) as resp:
            content = json.load(resp)["choices"][0]["message"]["content"]
    except HTTPError as e:
        raise ValueError(
            f"HTTP {e.code} from the model endpoint at step '{step}'. "
            f"Check your API key, endpoint URL, and model name."
        ) from e
    except URLError as e:
        raise ValueError(
            f"Could not reach the model endpoint at step '{step}': {e.reason}"
        ) from e

    # Write to temp file first to avoid partial writes on failure
    fd, tmp_path = tempfile.mkstemp(
        dir=cache_dir, prefix=f"{step}-attempt-", suffix=".txt"
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
        value = _decode(content)
        validate(value)
    except Exception as exc:
        raise ValueError(
            f"Model response failed validation at step '{step}'. "
            f"Raw reply saved to {tmp_path}. Error: {exc}"
        ) from exc

    # Promote temp file to canonical cache path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return value


def run_api(
    pack: Dict[int, List[dict]],
    url: str,
    model: str,
    api_key: str,
    cache_dir: Path,
    progress_cb: Callable[[str, float], None] | None = None,
) -> tuple[List[dict], dict]:
    """
    Full two-pass AI run.

    progress_cb(message, fraction_0_to_1) is called at each episode and before
    the ranking pass, so the UI can display a progress bar.

    Returns (reviews, ranking).
    """
    from .prompts import episode_prompt, ranking_prompt, EPISODE_SYSTEM, RANKING_SYSTEM
    from .validator import collect_picks

    n_eps    = len(pack)
    reviews: List[dict] = []

    for i, (ep, cues) in enumerate(pack.items()):
        if progress_cb:
            progress_cb(f"Analysing Episode {ep} …", i / (n_eps + 1))

        def _ep_validate(v, ep=ep, cues=cues):
            collect_picks({ep: cues}, [v])

        review = call_model(
            prompt=episode_prompt(ep, cues),
            system=EPISODE_SYSTEM,
            url=url,
            model=model,
            api_key=api_key,
            cache_dir=cache_dir,
            step=f"ep-{ep:03d}",
            validate=_ep_validate,
        )
        reviews.append(review)

    if not any(r["pick"] for r in reviews):
        return reviews, {"order": [], "montage": None}

    if progress_cb:
        progress_cb("Ranking nominations …", n_eps / (n_eps + 1))

    from .validator import resolve_ranking as _rr

    def _rank_validate(v):
        _rr(pack, reviews, v)

    ranking = call_model(
        prompt=ranking_prompt(pack, reviews),
        system=RANKING_SYSTEM,
        url=url,
        model=model,
        api_key=api_key,
        cache_dir=cache_dir,
        step="ranking",
        validate=_rank_validate,
    )
    return reviews, ranking

