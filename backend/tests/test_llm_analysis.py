"""WS5: Divyam client, redaction, FakeLLM transport, transcript analysis, rule-1 isolation."""
from __future__ import annotations

import ast
import json
import os

import pytest

from app import analysis, llm
from app.llm import FakeLLM, LLMNotConfigured, LLMSettings, complete, redact_phone_numbers

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(HERE), "app")


# --- redaction ---------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "call me on 9876543210 please",
    "mera number +91 98765 43210 hai",
    "+919876543210",
    "0 98765-43210 pe lagao",
    "91-9876543210",
])
def test_redacts_indian_phone_numbers(text):
    out = redact_phone_numbers(text)
    assert "[phone]" in out
    assert "9876543210" not in out.replace(" ", "").replace("-", "")


def test_redaction_leaves_times_ids_and_short_numbers_alone():
    text = "raat ke 12:10, 14416, 112, 1033, id 123456789012345, 8 km, 310 minutes"
    assert redact_phone_numbers(text) == text
    assert redact_phone_numbers("") == ""


# --- not configured -------------------------------------------------------------
def test_complete_raises_clear_error_when_base_url_empty(monkeypatch):
    for k in ("DIVYAM_BASE_URL", "DIVYAM_MODEL", "DIVYAM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(LLMNotConfigured) as exc:
        complete([{"role": "user", "content": "hi"}])
    assert "DIVYAM_BASE_URL" in str(exc.value)
    with pytest.raises(LLMNotConfigured):
        complete([{"role": "user", "content": "hi"}], settings=LLMSettings(base_url="https://x.invalid/v1", model=""))


# --- FakeLLM as transport: exercises the real request/response plumbing ----------
def test_complete_through_fake_transport_sends_redacted_messages_and_headers():
    fake = FakeLLM(responses={"transcript": '{"end_state": "unknown"}'}, default="namaste")
    settings = LLMSettings(base_url="https://divyam.invalid/v1", model="demo-model", api_key="sekrit",
                           auth_header="X-Api-Key", auth_scheme="")
    out = complete([{"role": "system", "content": "ring 9876543210"},
                    {"role": "user", "content": "hello"}], settings=settings, transport=fake)
    assert out == "namaste"
    call = fake.calls[0]
    assert call["url"] == "https://divyam.invalid/v1/chat/completions"
    assert call["headers"]["x-api-key"] == "sekrit"
    assert "authorization" not in call["headers"]
    assert call["messages"][0]["content"] == "ring [phone]"
    assert not call["json_mode"]


def test_complete_json_mode_sets_response_format_and_bearer_default():
    fake = FakeLLM(queue=['{"a": 1}'])
    settings = LLMSettings(base_url="https://divyam.invalid/v1/", model="m", api_key="k")
    assert complete([{"role": "user", "content": "x"}], json_mode=True, settings=settings, transport=fake) == '{"a": 1}'
    assert fake.calls[0]["json_mode"] is True
    assert fake.calls[0]["headers"]["authorization"] == "Bearer k"


def test_complete_raises_llmerror_on_http_error():
    import httpx

    transport = httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "no"}))
    settings = LLMSettings(base_url="https://divyam.invalid/v1", model="m", api_key="k")
    with pytest.raises(llm.LLMError) as exc:
        complete([{"role": "user", "content": "x"}], settings=settings, transport=transport)
    assert "401" in str(exc.value) and "k" not in str(exc.value).split("401")[0]


def test_fakellm_as_drop_in_complete_matches_substring_then_default():
    fake = FakeLLM(responses={"sleepy": "amber"}, default="green")
    assert fake([{"role": "user", "content": "driver sounds sleepy"}]) == "amber"
    assert fake([{"role": "user", "content": "all good"}]) == "green"
    assert fake.calls[0]["messages"][0]["content"] == "driver sounds sleepy"


# --- analysis ---------------------------------------------------------------------
TURNS = [
    {"role": "assistant", "en_text": "Ustaad, how are you?", "indic_text": "उस्ताद, कैसे हो?"},
    {"role": "user", "en_text": "Sleepy, eyes heavy. Call Sunita on 9876543210."},
    {"role": "assistant", "en_text": "Stop at Sharma Dhaba (demo) and sleep 20 minutes."},
    {"role": "user", "en_text": "Ok, parked."},
]


def test_analyse_transcript_parses_strict_json_and_redacts_outgoing():
    fake = FakeLLM(queue=[json.dumps({"end_state": "parked_resting", "sleep_signs": ["said sleepy", "eyes heavy"],
                                      "escalation_max": "red", "promised_stop": True, "stop_refused": False,
                                      "summary_en": "Driver stopped to rest."})])
    result = analysis.analyse_transcript(TURNS, complete=fake)
    assert result == {"end_state": "parked_resting", "sleep_signs": ["said sleepy", "eyes heavy"],
                      "escalation_max": "red", "promised_stop": True, "stop_refused": False,
                      "summary_en": "Driver stopped to rest."}
    assert list(result.keys()) == list(analysis.RESULT_KEYS)
    sent = fake.calls[0]["messages"][1]["content"]
    assert "[phone]" in sent and "9876543210" not in sent
    assert "DRIVER:" in sent and "KHALASI:" in sent and "उस्ताद" in sent
    assert fake.calls[0]["json_mode"] is True


@pytest.mark.parametrize("raw", ["", "not json at all", "[1, 2]", '{"end_state": "flying", "escalation_max": "purple"}',
                                 '```json\n{"end_state": "driving_alert", "sleep_signs": "yawn"}\n```'])
def test_analyse_transcript_safe_defaults_on_malformed_output(raw):
    result = analysis.analyse_transcript(TURNS, complete=FakeLLM(queue=[raw]))
    assert set(result) == set(analysis.RESULT_KEYS)
    assert result["end_state"] in analysis.END_STATES
    assert result["escalation_max"] in analysis.ESCALATIONS
    assert isinstance(result["sleep_signs"], list) and isinstance(result["promised_stop"], bool)
    assert result["summary_en"]
    if raw.startswith("```"):
        assert result["end_state"] == "driving_alert" and result["sleep_signs"] == ["yawn"]
    else:
        assert result["end_state"] == "unknown"


def test_analyse_transcript_never_raises_when_llm_unavailable(monkeypatch):
    monkeypatch.delenv("DIVYAM_BASE_URL", raising=False)
    result = analysis.analyse_transcript(TURNS)  # default complete -> LLMNotConfigured, swallowed
    assert result["end_state"] == "unknown" and "LLMNotConfigured" in result["summary_en"]
    assert analysis.analyse_transcript([])["summary_en"] == "No transcript."

    def boom(messages, **kw):
        raise RuntimeError("network")

    assert analysis.analyse_transcript(TURNS, complete=boom)["escalation_max"] == "green"


# --- rule 1: the decision engine never imports the LLM layer -----------------------
def test_engine_does_not_import_llm_or_analysis():
    with open(os.path.join(APP, "engine.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(a.name for a in node.names)
    for forbidden in ("llm", "analysis", "app.llm", "app.analysis"):
        assert forbidden not in imported, "engine.py must not import %s (rule 1)" % forbidden
