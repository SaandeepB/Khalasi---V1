"""Persona test harness: runs agents/khalasi.md in text mode against scripted drivers.

Text tool protocol (the Sarvam API tools, flattened to lines the model writes):
  TOOL truck_status                 -> harness answers with the stub JSON
  TOOL report_signal(type, detail)  -> recorded
  TOOL log_status(state)            -> recorded; "parked_resting" | "driving_alert"
Any other line is speech to the driver.

Modes:
  --fake   FakeLLM with canned agent turns per persona (fully offline, default when
           DIVYAM_BASE_URL is empty and --real is not given)
  --real   Divyam through backend/app/llm.py (settings from env; UNVERIFIED, open question 8)
The Khalasi instruction is used VERBATIM as the system prompt, with {{...}} filled from
personas.json demo_variables; the tool protocol is a second system message.
Python 3.9 compatible.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

from app import llm as llm_mod  # noqa: E402
from evals import judge  # noqa: E402

PERSONAS_PATH = os.path.join(ROOT, "evals", "personas.json")
PROMPT_PATH = os.path.join(ROOT, "agents", "khalasi.md")
REPORT_DIR = os.path.join(ROOT, "evals", "reports")

TOOL_PROTOCOL = (
    "TEXT MODE. This is a text rehearsal of a phone call. Your tools are plain lines at the START of your reply:\n"
    "TOOL truck_status\n"
    "TOOL report_signal(type, detail)\n"
    "TOOL log_status(state)\n"
    "After any TOOL lines, write exactly what you would SAY to the driver (no quotes, no labels). "
    "Tool results arrive as a message starting with TOOL_RESULT. The driver's words arrive as the user. "
    "Your opening line has already been spoken for you."
)

TOOL_LINE_RE = re.compile(r"^\s*TOOL\s+(\w+)\s*(?:\((.*)\))?\s*$")


def stub_truck_status(dark_stretch: bool = False) -> Dict[str, Any]:
    """Demo data (simulated): moving, 310 min since rest, Jhansi 3 h away."""
    return {
        "time_now": "00:10", "moving": True, "speed_kmph": 52, "gps_age_sec": 20,
        "stopped_at": None, "location_text": "NH-44 near Sagar (demo)",
        "trip_started_at": "19:00", "last_rest_ended_at": "19:00", "minutes_since_last_rest": 310,
        "next_safe_stop": {"name": "Apna Ghar (demo)" if dark_stretch else "Sharma Dhaba (demo)",
                           "type": "apna_ghar" if dark_stretch else "dhaba", "distance_km": 8, "lit": True, "staffed": True},
        "dark_stretch": ({"name": "Sagar-Lalitpur stretch (demo data, not real coverage)",
                          "starts_in_min": 15, "length_min": 40} if dark_stretch else None),
        "destination": "Jhansi", "eta_min": 180, "risk_window": True, "simulated": True,
    }


def load_personas(path: str = PERSONAS_PATH) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def system_prompt(persona: Dict[str, Any], variables: Dict[str, str], path: str = PROMPT_PATH) -> str:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    filled = dict(variables)
    filled["first_call_tonight"] = persona.get("first_call_tonight", "no")
    filled["call_reason"] = persona.get("call_reason", "check_in")
    for key, value in filled.items():
        text = text.replace("{{%s}}" % key, str(value))
    return text


def parse_tool_args(raw: Optional[str]) -> List[str]:
    if raw is None:
        return []
    return [a.strip().strip('"').strip("'") for a in raw.split(",", 1)]


def parse_agent_output(text: str) -> Dict[str, Any]:
    tools: List[Dict[str, Any]] = []
    speech: List[str] = []
    for line in text.splitlines():
        m = TOOL_LINE_RE.match(line)
        if m:
            tools.append({"name": m.group(1), "args": parse_tool_args(m.group(2))})
        elif line.strip():
            speech.append(line.strip())
    return {"tools": tools, "text": " ".join(speech)}


class Persona:
    def __init__(self, spec: Dict[str, Any], complete: Optional[Any] = None) -> None:
        self.spec = spec
        self.complete = complete  # None -> scripted replies only
        self.i = 0

    def reply(self, history: Sequence[Dict[str, str]]) -> str:
        scripted = self.spec.get("driver_replies", [])
        fallback = scripted[min(self.i, len(scripted) - 1)] if scripted else "Haan."
        self.i += 1
        if self.complete is None:
            return fallback
        msgs = [{"role": "system", "content": "You are a truck driver on a phone call. Persona: %s Reply with one or two short "
                 "spoken sentences in the driver's own words, Hinglish by default. Never break character." % self.spec["brief"]}]
        for h in history:
            msgs.append({"role": "user" if h["role"] == "agent" else "assistant", "content": h["text"]})
        try:
            out = self.complete(msgs).strip()
            return out or fallback
        except Exception as exc:  # real persona model unavailable: fall back to the script
            print("persona model failed (%s), using scripted reply" % type(exc).__name__, file=sys.stderr)
            return fallback


def run_persona(persona: Dict[str, Any], variables: Dict[str, str], complete: Any, persona_model: Optional[Any],
                turns: int) -> Dict[str, Any]:
    status = stub_truck_status(bool(persona.get("dark_stretch")))
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt(persona, variables)},
                                      {"role": "system", "content": TOOL_PROTOCOL}]
    first_line = {"inbound": "Ustaad! Khalasi bol raha hoon.",
                  "dark_stretch_warning": "Ustaad! Khalasi. Ek zaroori baat, aage network nahi milega."}.get(
        persona.get("call_reason", ""), "Ustaad! Khalasi bol raha hoon. Bas haal-chaal poochne ke liye. Kahan pahunche?")
    messages.append({"role": "assistant", "content": first_line})
    driver = Persona(persona, persona_model)
    transcript: List[Dict[str, Any]] = [{"role": "agent", "text": first_line, "tools": [], "moving": True, "system_line": True}]
    history: List[Dict[str, str]] = [{"role": "agent", "text": first_line}]
    ended = False
    for _ in range(turns):
        reply = driver.reply(history)
        transcript.append({"role": "driver", "text": reply})
        history.append({"role": "driver", "text": reply})
        messages.append({"role": "user", "content": reply})
        tools_this_turn: List[Dict[str, Any]] = []
        spoken = ""
        for _round in range(3):
            raw = complete(messages)
            messages.append({"role": "assistant", "content": raw})
            parsed = parse_agent_output(raw)
            results: List[str] = []
            for tool in parsed["tools"]:
                if tool["name"] == "truck_status":
                    tool["result"] = json.dumps(status)
                    results.append("TOOL_RESULT truck_status: " + tool["result"])
                else:
                    tool["result"] = "ok"
                    results.append("TOOL_RESULT %s: ok" % tool["name"])
                tools_this_turn.append(tool)
            spoken = parsed["text"]
            if spoken or not parsed["tools"]:
                break
            messages.append({"role": "user", "content": "\n".join(results)})
        transcript.append({"role": "agent", "text": spoken, "tools": tools_this_turn, "moving": bool(status["moving"])})
        history.append({"role": "agent", "text": spoken})
        if any(t["name"] == "log_status" for t in tools_this_turn):
            ended = True
            break
    return {"persona": persona["id"], "transcript": transcript, "truck_status": status, "ended": ended}


def fake_llm_for(persona: Dict[str, Any]) -> llm_mod.FakeLLM:
    return llm_mod.FakeLLM(queue=list(persona.get("fake_agent_turns", [])), default="Haan Ustaad, bolo.")


def llm_judge_summary(results: Sequence[Dict[str, Any]], complete: Any) -> Optional[str]:
    try:
        table = "\n".join("%s: %s" % (r["name"], "PASS" if r["pass"] else "FAIL " + "; ".join(
            c["note"] for c in r["checks"].values() if not c["pass"])) for r in results)
        return complete([{"role": "system", "content": "You review eval results for a voice safety agent. Two or three sentences."},
                         {"role": "user", "content": "Rubric results:\n" + table + "\nSummarise the main weaknesses."}])
    except Exception as exc:
        return "LLM judge summary unavailable (%s)." % type(exc).__name__


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--fake", action="store_true", help="canned agent lines, no network (default when Divyam is not configured)")
    mode.add_argument("--real", action="store_true", help="use Divyam via backend/app/llm.py (UNVERIFIED settings)")
    ap.add_argument("--turns", type=int, default=6, help="max driver turns per persona")
    ap.add_argument("--only", help="comma-separated persona ids")
    ap.add_argument("--report", default=os.path.join(REPORT_DIR, "latest.md"))
    args = ap.parse_args(argv)

    settings = llm_mod.LLMSettings.from_env()
    fake = args.fake or (not args.real and not settings.configured)
    if args.real and not settings.configured:
        print("DIVYAM_BASE_URL is empty; cannot run --real. Use --fake.", file=sys.stderr)
        return 2

    data = load_personas()
    variables = data.get("demo_variables", {})
    personas = data["personas"]
    if args.only:
        wanted = {p.strip() for p in args.only.split(",")}
        personas = [p for p in personas if p["id"] in wanted]

    results: List[Dict[str, Any]] = []
    transcripts: Dict[str, Any] = {}
    runs: List[Dict[str, Any]] = []
    for persona in personas:
        if fake:
            complete = fake_llm_for(persona)
            persona_model = None
        else:
            complete = lambda msgs, _s=settings: llm_mod.complete(msgs, settings=_s)  # noqa: E731
            persona_model = complete
        run = run_persona(persona, variables, complete, persona_model, args.turns)
        verdict = judge.judge_transcript(persona, run["transcript"], run["truck_status"])
        results.append(verdict)
        transcripts[persona["id"]] = run["transcript"]
        runs.append({"persona": persona["id"], "ended": run["ended"], "transcript": run["transcript"], "verdict": verdict})
        print("%-28s %s" % (persona["name"], "PASS" if verdict["pass"] else "FAIL: " + "; ".join(
            "%s (%s)" % (k, c["note"]) for k, c in verdict["checks"].items() if not c["pass"])))

    summary = None if fake else llm_judge_summary(results, complete)
    meta = {"mode": "fake (FakeLLM, simulated)" if fake else "real (Divyam, model=%s)" % settings.model,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M IST"), "turn budget": args.turns,
            "system prompt": "agents/khalasi.md verbatim + text tool protocol"}
    report = judge.render_report(results, transcripts, fake, summary, meta)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(report)
    with open(os.path.splitext(args.report)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump({"fake": fake, "meta": meta, "runs": runs}, fh, indent=1, ensure_ascii=False)
    print("report: %s (%d/%d pass)" % (args.report, sum(r["pass"] for r in results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
