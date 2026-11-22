"""Post-call transcript analysis through Divyam (Workstream 5, offline only).

``analyse_transcript`` turns a Sarvam ``interaction_transcript`` into a small,
fixed-shape JSON summary for the demo console and pilot metrics:

    {"end_state": "parked_resting" | "driving_alert" | "unknown",
     "sleep_signs": [str], "escalation_max": "green" | "amber" | "red",
     "promised_stop": bool, "stop_refused": bool, "summary_en": str}

RULE 1 (MASTER_PROMPT section 2): this result is for CONSOLE LABELS and PILOT
METRICS ONLY. It must never trigger, delay or cancel a call, call-back or alert.
The decision engine (``engine.py``) does not import this module or ``llm.py``;
``backend/tests/test_llm_analysis.py`` asserts that.

Privacy: phone numbers are redacted by ``llm.complete`` before anything leaves the
box, and only ``en_text``/``indic_text`` are sent, never numbers or metadata.
Malformed or missing model output degrades to safe defaults (``unknown`` /
``green`` / empty), never to an exception. Python 3.9 compatible.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

from .llm import complete as _default_complete

__all__ = ["analyse_transcript", "build_messages", "parse_analysis", "default_analysis",
           "END_STATES", "ESCALATIONS", "RESULT_KEYS"]

END_STATES = ("parked_resting", "driving_alert", "unknown")
ESCALATIONS = ("green", "amber", "red")
RESULT_KEYS = ("end_state", "sleep_signs", "escalation_max", "promised_stop", "stop_refused", "summary_en")

MAX_TURNS = 200
MAX_TURN_CHARS = 600
MAX_SIGNS = 12
MAX_SUMMARY_CHARS = 400

SYSTEM_PROMPT = (
    "You are an analyst for Khalasi, a voice co-rider for Indian truck drivers. "
    "You will read a call transcript between the agent (Khalasi) and a driver and return "
    "ONLY a JSON object, no prose, no markdown, with exactly these keys:\n"
    '{"end_state": "parked_resting" | "driving_alert" | "unknown",\n'
    ' "sleep_signs": [short English strings, each one observed sleep sign, [] if none],\n'
    ' "escalation_max": "green" | "amber" | "red",\n'
    ' "promised_stop": true | false,\n'
    ' "stop_refused": true | false,\n'
    ' "summary_en": one or two plain English sentences}\n'
    "Rules: end_state is parked_resting only if the driver clearly stopped to rest, "
    "driving_alert if still driving and alert, otherwise unknown. escalation_max is the highest "
    "level the agent reached: green = no sleep sign, amber = one sign / chai break suggested, "
    "red = firm stop demanded. This output is used for labels and metrics only. "
    "Do not include phone numbers, names of contacts or any advice."
)


def default_analysis(summary: str = "") -> Dict[str, Any]:
    return {"end_state": "unknown", "sleep_signs": [], "escalation_max": "green",
            "promised_stop": False, "stop_refused": False, "summary_en": summary}


def _turn_text(turn: Dict[str, Any]) -> str:
    en = str(turn.get("en_text") or turn.get("text") or "").strip()
    indic = str(turn.get("indic_text") or "").strip()
    if en and indic and en != indic:
        text = "%s  [%s]" % (en, indic)
    else:
        text = en or indic
    return text[:MAX_TURN_CHARS]


def _role_label(turn: Dict[str, Any]) -> str:
    role = str(turn.get("role", "")).lower()
    if role in ("user", "driver", "human"):
        return "DRIVER"
    if role in ("tool", "function", "system"):
        return role.upper()
    return "KHALASI"


def format_transcript(turns: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for turn in list(turns)[:MAX_TURNS]:
        if not isinstance(turn, dict):
            continue
        text = _turn_text(turn)
        if not text:
            continue
        lines.append("%s: %s" % (_role_label(turn), text))
    return "\n".join(lines) if lines else "(empty transcript)"


def build_messages(turns: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Transcript:\n" + format_transcript(turns) + "\n\nReturn the JSON object now."},
    ]


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _loads_lenient(raw: str) -> Optional[Dict[str, Any]]:
    """Parse JSON, tolerating code fences and prose around the object."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    for candidate in (text, (_JSON_BLOCK_RE.search(text) or re.match("", "")).group(0)):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "haan")
    return False


def parse_analysis(raw: str) -> Dict[str, Any]:
    """Validate model output into the exact result shape; safe defaults on anything odd."""
    data = _loads_lenient(raw)
    result = default_analysis()
    if data is None:
        return result

    end_state = str(data.get("end_state", "")).strip().lower()
    result["end_state"] = end_state if end_state in END_STATES else "unknown"

    signs = data.get("sleep_signs")
    if isinstance(signs, str):
        signs = [signs] if signs.strip() else []
    clean: List[str] = []
    if isinstance(signs, list):
        for s in signs:
            if isinstance(s, (str, int, float)) and str(s).strip():
                clean.append(str(s).strip()[:120])
            if len(clean) >= MAX_SIGNS:
                break
    result["sleep_signs"] = clean

    esc = str(data.get("escalation_max", "")).strip().lower()
    result["escalation_max"] = esc if esc in ESCALATIONS else "green"
    result["promised_stop"] = _as_bool(data.get("promised_stop"))
    result["stop_refused"] = _as_bool(data.get("stop_refused"))
    summary = data.get("summary_en", "")
    result["summary_en"] = str(summary).strip()[:MAX_SUMMARY_CHARS] if isinstance(summary, (str, int, float)) else ""
    return result


def analyse_transcript(turns: Sequence[Dict[str, Any]],
                       complete: Callable[..., str] = _default_complete) -> Dict[str, Any]:
    """Analyse a webhook ``interaction_transcript`` (list of {role, en_text, indic_text?}).

    Labels and metrics only (rule 1). Never raises on model trouble: when Divyam is not
    configured, errors, or returns junk, the safe default is returned with ``summary_en``
    explaining why.
    """
    if not turns:
        return default_analysis("No transcript.")
    try:
        raw = complete(build_messages(turns), json_mode=True)
    except Exception as exc:  # LLMNotConfigured, network, or anything else: labels only
        return default_analysis("Analysis unavailable (%s)." % type(exc).__name__)
    result = parse_analysis(raw)
    if not result["summary_en"]:
        result["summary_en"] = "Analysis returned no summary."
    return result
