"""Divyam LLM client (Workstream 5, offline only).

Thin OpenAI-compatible chat-completions client used ONLY for post-call analysis
and the persona eval harness. It never decides anything about calls or alerts
(MASTER_PROMPT rule 1).

UNVERIFIED (open question 8 in docs/open-questions.md): the Divyam base URL,
the auth header name/scheme, the request/response shape and the model names
below are ASSUMPTIONS modelled on the OpenAI chat-completions API. They have
not been checked against the Divyam dashboard or docs because no credentials
were available. Confirm every one of them before any Live use:

- ``DIVYAM_BASE_URL``     e.g. ``https://<host>/v1`` (we POST ``/chat/completions``)
- ``DIVYAM_MODEL``        model id string as shown in the Divyam dashboard
- ``DIVYAM_AUTH_HEADER``  header name, default ``Authorization``
- ``DIVYAM_AUTH_SCHEME``  prefix before the key, default ``Bearer`` ("" for none)
- ``DIVYAM_API_KEY``      secret, from ``.env`` only (rule 5), never logged
- ``DIVYAM_TIMEOUT_S``    optional, default 30

Privacy (rule 4, section 8): every outgoing message is passed through
``redact_phone_numbers`` so Indian phone numbers never leave the box.
The HTTP transport is injectable (``httpx.BaseTransport`` or a callable) so
tests and the ``--fake`` harness never touch the network. Python 3.9 compatible.
"""
from __future__ import annotations

import json
import os
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Union

__all__ = [
    "LLMError",
    "LLMNotConfigured",
    "LLMSettings",
    "FakeLLM",
    "complete",
    "redact_phone_numbers",
    "PHONE_MASK",
]

PHONE_MASK = "[phone]"

# Indian mobile/landline-ish numbers: optional +91 / 91 / 0 prefix, then 10 digits,
# allowing spaces or hyphens between groups. Word-boundary guarded on both sides
# so that 12-digit ids or timestamps are not eaten.
_PHONE_RE = re.compile(
    r"(?<![\d])"
    r"(?:\+?91[\s\-]?|0)?"
    r"(?:\d[\s\-]?){9}\d"
    r"(?![\d])"
)


def redact_phone_numbers(text: str) -> str:
    """Mask Indian phone numbers (10 digits, optional +91/0 prefix) with ``[phone]``."""
    if not text:
        return text

    def _sub(m: "re.Match[str]") -> str:
        digits = re.sub(r"\D", "", m.group(0))
        # 10 plain digits, 11 with leading 0, 12 with 91: anything else is not a phone.
        if len(digits) in (10, 11, 12):
            return PHONE_MASK
        return m.group(0)

    return _PHONE_RE.sub(_sub, text)


class LLMError(RuntimeError):
    """Base class for LLM client errors."""


class LLMNotConfigured(LLMError):
    """Raised when DIVYAM_BASE_URL (or the model) is empty: nothing can be sent."""


@dataclass
class LLMSettings:
    """Divyam connection settings. All values are UNVERIFIED assumptions (open question 8)."""

    base_url: str = ""
    model: str = ""
    api_key: str = ""
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> "LLMSettings":
        e = os.environ.get
        try:
            timeout = float(e("DIVYAM_TIMEOUT_S", "30") or "30")
        except ValueError:
            timeout = 30.0
        return cls(
            base_url=(e("DIVYAM_BASE_URL", "") or "").strip(),
            model=(e("DIVYAM_MODEL", "") or "").strip(),
            api_key=(e("DIVYAM_API_KEY", "") or "").strip(),
            auth_header=(e("DIVYAM_AUTH_HEADER", "") or "Authorization").strip() or "Authorization",
            auth_scheme=(e("DIVYAM_AUTH_SCHEME", "Bearer") if e("DIVYAM_AUTH_SCHEME") is not None else "Bearer").strip(),
            timeout_s=timeout,
        )

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def headers(self) -> Dict[str, str]:
        value = ("%s %s" % (self.auth_scheme, self.api_key)).strip() if self.auth_scheme else self.api_key
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers[self.auth_header] = value
        return headers

    def completions_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"


Message = Dict[str, str]


def _redact_messages(messages: Sequence[Message]) -> List[Message]:
    out: List[Message] = []
    for m in messages:
        role = str(m.get("role", "user"))
        content = redact_phone_numbers(str(m.get("content", "")))
        out.append({"role": role, "content": content})
    return out


def _extract_content(data: Any) -> str:
    """Pull the assistant text out of an OpenAI-style response. Shape UNVERIFIED for Divyam."""
    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] or {}
            msg = first.get("message") if isinstance(first, dict) else None
            if isinstance(msg, dict) and msg.get("content") is not None:
                return str(msg.get("content"))
            if isinstance(first, dict) and first.get("text") is not None:
                return str(first.get("text"))
        if data.get("content") is not None:          # some gateways flatten the reply
            return str(data["content"])
        if data.get("output_text") is not None:
            return str(data["output_text"])
    raise LLMError("unexpected completion response shape: keys=%s"
                   % (sorted(data.keys()) if isinstance(data, dict) else type(data).__name__))


class FakeLLM:
    """Canned LLM for tests and ``--fake`` mode.

    Use it either as ``transport=`` (it then behaves like an ``httpx`` mock transport
    and the real request/response plumbing is exercised), or call it directly as a
    drop-in for ``complete`` (``fake(messages, json_mode=...) -> str``).

    Responses come from, in order: a FIFO ``queue`` of strings, then ``responses``
    (a dict of substring -> reply, matched against the LAST message content and
    then the whole prompt), then ``default``.
    Every request is recorded in ``calls`` (redacted messages, as sent).
    """

    def __init__(self, responses: Optional[Dict[str, str]] = None, queue: Optional[Sequence[str]] = None,
                 default: str = "") -> None:
        self.responses: Dict[str, str] = dict(responses or {})
        self.queue: Deque[str] = deque(queue or [])
        self.default = default
        self.calls: List[Dict[str, Any]] = []

    # --- as a drop-in `complete` -------------------------------------------
    def reply_for(self, messages: Sequence[Message]) -> str:
        if self.queue:
            return self.queue.popleft()
        last = str(messages[-1].get("content", "")) if messages else ""
        for needle, reply in self.responses.items():
            if needle and needle in last:
                return reply
        joined = "\n".join(str(m.get("content", "")) for m in messages)
        for needle, reply in self.responses.items():
            if needle and needle in joined:
                return reply
        return self.default

    def __call__(self, messages: Sequence[Message], *, json_mode: bool = False,
                 settings: Optional[LLMSettings] = None, transport: Any = None) -> str:
        redacted = _redact_messages(messages)
        self.calls.append({"messages": redacted, "json_mode": json_mode})
        return self.reply_for(redacted)

    # --- as an httpx transport ---------------------------------------------
    def as_httpx_transport(self) -> Any:
        import httpx

        fake = self

        def handler(request: "httpx.Request") -> "httpx.Response":
            try:
                body = json.loads(request.content.decode("utf-8") or "{}")
            except ValueError:
                body = {}
            messages = body.get("messages") or []
            fake.calls.append({"messages": messages, "json_mode": bool(body.get("response_format")),
                               "url": str(request.url), "headers": dict(request.headers)})
            reply = fake.reply_for(messages)
            payload = {"id": "fake-%d" % len(fake.calls), "object": "chat.completion",
                       "model": body.get("model", "fake"),
                       "choices": [{"index": 0, "finish_reason": "stop",
                                    "message": {"role": "assistant", "content": reply}}]}
            return httpx.Response(200, json=payload)

        return httpx.MockTransport(handler)


def complete(messages: Sequence[Message], *, json_mode: bool = False,
             settings: Optional[LLMSettings] = None,
             transport: Any = None) -> str:
    """Send a chat completion to Divyam and return the assistant text.

    ``transport`` may be an ``httpx.BaseTransport``, a ``FakeLLM``, or ``None`` (real HTTP).
    Raises ``LLMNotConfigured`` when ``DIVYAM_BASE_URL`` is empty, ``LLMError`` on bad
    HTTP status or an unexpected response body. Phone numbers are redacted first.
    """
    cfg = settings or LLMSettings.from_env()
    if not cfg.configured:
        raise LLMNotConfigured(
            "DIVYAM_BASE_URL is empty: Divyam is not configured (offline-only build; "
            "base URL, auth header and model are unverified, see open question 8)")
    if not cfg.model:
        raise LLMNotConfigured("DIVYAM_MODEL is empty: set the model id from the Divyam dashboard")

    redacted = _redact_messages(messages)
    if isinstance(transport, FakeLLM):
        transport = transport.as_httpx_transport()

    import httpx  # lazy: tests without network still import this module cheaply

    body: Dict[str, Any] = {"model": cfg.model, "messages": redacted, "temperature": 0.2}
    if json_mode:
        body["response_format"] = {"type": "json_object"}   # OpenAI-style; UNVERIFIED for Divyam

    try:
        with httpx.Client(transport=transport, timeout=cfg.timeout_s) as client:
            resp = client.post(cfg.completions_url(), headers=cfg.headers(), json=body)
    except httpx.HTTPError as exc:   # never include headers (the key) in the message
        raise LLMError("Divyam request failed: %s" % type(exc).__name__) from exc
    if resp.status_code >= 400:
        raise LLMError("Divyam returned HTTP %d" % resp.status_code)
    try:
        data = resp.json()
    except ValueError as exc:
        raise LLMError("Divyam returned non-JSON body") from exc
    return _extract_content(data)
