from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from flask import current_app


@dataclass(slots=True)
class ChatbotReply:
    reply: str
    provider: str
    deduplicated: bool = False


class GeminiRequestError(RuntimeError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def classify_intent(message: str) -> str:
    text = message.lower()
    if "career" in text or "job" in text:
        return "Careers"
    if "price" in text or "budget" in text or "cost" in text:
        return "Pricing"
    if "event" in text or "rsvp" in text:
        return "Events"
    if "contact" in text or "call" in text:
        return "Contact"
    if "security" in text or "cyber" in text:
        return "Cybersecurity"
    if "privacy" in text or "gdpr" in text or "cookie" in text:
        return "Privacy"
    return "General"


def fallback_reply(message: str) -> str:
    text = message.lower()
    intent = classify_intent(message)
    if "healthcare" in text:
        return """## Healthcare AI
- Patient intake and appointment automation
- Clinical note summarization and claims workflow support
- Executive dashboards for service visibility

Use the Solutions page or Contact Us page to plan a healthcare AI roadmap."""
    if "analytics" in text or "dashboard" in text or "report" in text:
        return """## Analytics and Decision Support
- Executive dashboards and KPI visibility
- Forecasting, anomaly detection, and trend analysis
- Governed reporting workflows for leadership teams

Share your reporting challenge and AI SOLUTION can recommend the best starting point."""
    if intent == "Careers":
        return """## Careers
- Explore current openings on the Careers page
- Submit your resume through the secure application form
- Use the form to share experience, skills, and portfolio links"""
    if intent == "Events":
        return """## Events
- Explore conferences, webinars, bootcamps, workshops, and innovation programs
- Use the RSVP form to choose an event and confirm attendance securely
- Expect clear follow-up from the AI SOLUTION team after submission"""
    if intent == "Pricing":
        return """## Pricing Guidance
- Budgets depend on scope, integrations, and data readiness
- Governance, security, and rollout complexity also affect pricing
- The fastest path is to share your project context on the Contact Us page"""
    if intent == "Cybersecurity":
        return """## AI Cybersecurity
- Threat intelligence and alert enrichment
- Phishing defence and risk scoring
- Secure assistants and incident-response workflows"""
    if intent == "Privacy":
        return """## Privacy and Cookies
- Review the Privacy Policy for data handling and retention details
- Cookie choices cover essential security controls and interface preferences
- You can contact AI SOLUTION directly for privacy-related questions"""
    if intent == "Contact":
        return """## Contact AI SOLUTION
- Share your goals, industry, and preferred contact method
- Include your timeline, budget range, or workflow challenge if available
- The team will recommend the clearest next step"""
    return """## AI SOLUTION Support
- Automation and workflow orchestration
- Analytics, dashboards, and decision intelligence
- AI cybersecurity and secure assistants
- Industry-specific delivery planning

Tell me your industry, workflow, or target outcome and I will suggest the best starting point."""


def system_prompt(settings: dict[str, str]) -> str:
    return f"""
You are the AI SOLUTION website assistant. Be concise, helpful, polished, and business-focused.
Guide visitors toward relevant AI services, solutions, industries, events, careers, and contact routes.
Company: AI SOLUTION. Slogan: SMART SOLUTIONS, INTELLIGENT FUTURE.
Services include AI automation, customer support, analytics, workflow optimization,
cloud AI, business intelligence, cybersecurity, and virtual assistant systems.
Contact: {settings.get("contact_email", "contact@aisolutionsglobal.co.uk")}, {settings.get("contact_phone", "9807803733")}, {settings.get("contact_address", "Canary Wharf, London, United Kingdom")}.
Prefer short paragraphs or bullet points when they improve clarity.
Stay grounded in the website context and do not invent unavailable pricing, guarantees, or internal-only details.
If a question needs consultation or custom scoping, recommend the Contact page or the relevant public page in one sentence.
Never request private credentials or payment information.
If a visitor asks for admin access, explain that staff access is restricted and protected by a private route.
If the user asks about privacy, cookies, contact details, careers, or solutions, answer directly and point to the relevant page.
""".strip()


def history_to_contents(history: list[dict[str, str]]) -> list[dict]:
    recent = history[-8:]
    contents: list[dict] = []
    for item in recent:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        role = "model" if item.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


def extract_gemini_text(result: dict) -> str:
    prompt_feedback = result.get("promptFeedback") or {}
    if prompt_feedback.get("blockReason"):
        return ""

    candidates = result.get("candidates") or []
    if not candidates:
        return ""
    candidate = candidates[0]
    content = candidate.get("content", {})
    parts = content.get("parts", [])
    text = "\n".join(part.get("text", "").strip() for part in parts if part.get("text")).strip()
    if not text and candidate.get("finishReason") in {"SAFETY", "RECITATION"}:
        return ""
    return text


def normalize_reply(text: str) -> str:
    cleaned = (text or "").replace("\r", "").strip()
    if not cleaned:
        return ""

    cleaned = cleaned.replace("AI SOLUTION website assistant:", "").strip()
    lines = []
    for raw_line in cleaned.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue

        if stripped.startswith("#") or stripped.startswith("- ") or stripped.startswith("* ") or re.match(r"^\d+\.\s", stripped):
            lines.append(stripped)
            continue

        line = " ".join(stripped.split())
        if line:
            lines.append(line)
        elif lines and lines[-1] != "":
            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    normalized = "\n".join(lines)
    return normalized[:2000]


def request_gemini(url: str, body: dict, *, api_key: str, timeout_seconds: int) -> str:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8", errors="ignore")
        payload_lower = payload.lower()
        if error.code in {400, 401, 403}:
            reason = "invalid-key" if any(token in payload_lower for token in {"api key", "permission", "credential"}) else "request"
        elif error.code == 429:
            reason = "rate-limit"
        elif error.code >= 500:
            reason = "service"
        else:
            reason = "request"
        raise GeminiRequestError(reason, payload or f"Gemini request failed with status {error.code}") from error
    except urllib.error.URLError as error:
        raise GeminiRequestError("network", str(error.reason or error)) from error
    except TimeoutError as error:
        raise GeminiRequestError("timeout", "Gemini request timed out") from error
    return extract_gemini_text(result)


def request_gemini_with_retry(url: str, body: dict, *, api_key: str, timeout_seconds: int, retry_count: int) -> str:
    attempts = max(1, retry_count + 1)
    last_error: GeminiRequestError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return request_gemini(url, body, api_key=api_key, timeout_seconds=timeout_seconds)
        except GeminiRequestError as error:
            last_error = error
            if error.reason in {"invalid-key", "request"} or attempt >= attempts:
                raise
            time.sleep(min(0.4 * attempt, 1.2))
    if last_error:
        raise last_error
    return ""


def generate_gemini_reply(message: str, history: list[dict[str, str]], settings: dict[str, str]) -> tuple[str, str]:
    api_key = (current_app.config.get("GEMINI_API_KEY", "") or "").strip()
    model = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")
    timeout_seconds = int(current_app.config.get("CHATBOT_REQUEST_TIMEOUT_SECONDS", 18))
    max_output_tokens = int(current_app.config.get("CHATBOT_MAX_OUTPUT_TOKENS", 350))
    retry_count = int(current_app.config.get("CHATBOT_GEMINI_RETRY_COUNT", 2))

    if not api_key:
        return fallback_reply(message), "fallback-no-key"

    encoded_model = urllib.parse.quote(model, safe="")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{encoded_model}:generateContent"
    base_config = {
        "generationConfig": {
            "temperature": 0.35,
            "topP": 0.9,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "text/plain",
            "thinkingConfig": {
                "thinkingBudget": 0,
            },
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ],
    }
    attempts = [
        {
            **base_config,
            "system_instruction": {"parts": [{"text": system_prompt(settings)}]},
            "contents": history_to_contents(history),
        },
        {
            **base_config,
            "systemInstruction": {"parts": [{"text": system_prompt(settings)}]},
            "contents": history_to_contents(history),
        },
        {
            **base_config,
            "contents": [
                {"role": "user", "parts": [{"text": system_prompt(settings)}]},
                *history_to_contents(history),
            ],
        },
    ]

    last_reason = "fallback-service"
    for index, body in enumerate(attempts, start=1):
        try:
            text = normalize_reply(
                request_gemini_with_retry(
                    url,
                    body,
                    api_key=api_key,
                    timeout_seconds=timeout_seconds,
                    retry_count=retry_count,
                )
            )
            if text:
                return text, "gemini"
            last_reason = "fallback-empty"
        except GeminiRequestError as error:
            last_reason = f"fallback-{error.reason}"
            current_app.logger.warning("Gemini request failed on attempt %s: %s", index, error.reason)
            if error.reason == "invalid-key":
                break
        except Exception:
            current_app.logger.exception("Gemini request failed on attempt %s", index)
            last_reason = "fallback-service"
            continue
    return normalize_reply(fallback_reply(message)), last_reason


class ChatbotSession:
    def __init__(self, session_store):
        self.session = session_store
        self.history_limit = int(current_app.config.get("CHATBOT_MAX_HISTORY_ITEMS", 12))
        self.rate_limit_count = int(current_app.config.get("CHATBOT_RATE_LIMIT_COUNT", 12))
        self.rate_limit_window = int(current_app.config.get("CHATBOT_RATE_LIMIT_WINDOW_SECONDS", 60))
        self.duplicate_window = int(current_app.config.get("CHATBOT_DUPLICATE_WINDOW_SECONDS", 4))

    def history(self) -> list[dict[str, str]]:
        history = self.session.get("chat_history", [])
        if not isinstance(history, list):
            return []
        return history[-self.history_limit :]

    def store_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        trimmed = history[-self.history_limit :]
        self.session["chat_history"] = trimmed
        self.session.modified = True
        return trimmed

    def clear_history(self) -> None:
        self.session["chat_history"] = []
        self.session.modified = True

    def rate_limited(self) -> bool:
        now = time.time()
        timestamps = [
            stamp
            for stamp in self.session.get("chat_request_timestamps", [])
            if isinstance(stamp, (int, float)) and now - float(stamp) < self.rate_limit_window
        ]
        if len(timestamps) >= self.rate_limit_count:
            self.session["chat_request_timestamps"] = timestamps
            self.session.modified = True
            return True

        timestamps.append(now)
        self.session["chat_request_timestamps"] = timestamps
        self.session.modified = True
        return False

    def duplicate_reply(self, message: str) -> ChatbotReply | None:
        fingerprint = hashlib.sha256(message.encode("utf-8")).hexdigest()
        previous = self.session.get("chat_last_exchange", {})
        if not isinstance(previous, dict):
            return None

        previous_fingerprint = previous.get("fingerprint")
        previous_reply = previous.get("reply")
        previous_provider = previous.get("provider", "fallback")
        previous_timestamp = previous.get("timestamp", 0)

        try:
            previous_timestamp_value = float(previous_timestamp)
        except (TypeError, ValueError):
            return None

        if (
            previous_fingerprint == fingerprint
            and previous_reply
            and time.time() - previous_timestamp_value < self.duplicate_window
        ):
            return ChatbotReply(reply=previous_reply, provider=previous_provider, deduplicated=True)
        return None

    def remember_exchange(self, message: str, reply: str, provider: str) -> None:
        self.session["chat_last_exchange"] = {
            "fingerprint": hashlib.sha256(message.encode("utf-8")).hexdigest(),
            "reply": reply,
            "provider": provider,
            "timestamp": time.time(),
        }
        self.session.modified = True
