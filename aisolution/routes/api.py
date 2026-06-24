from __future__ import annotations

import secrets

from flask import Blueprint, current_app, jsonify, request, session

from ..extensions import db
from ..models import ChatbotLog
from ..services.chatbot import ChatbotSession, classify_intent, generate_gemini_reply
from ..utils.security import client_ip, sanitize_text
from ..utils.site import active_settings_map


api_bp = Blueprint("api", __name__)


@api_bp.get("/chat/history")
def chat_history():
    history = ChatbotSession(session).history()
    return jsonify({"history": history})


@api_bp.post("/chat/clear")
def clear_chat_history():
    ChatbotSession(session).clear_history()
    return jsonify({"ok": True})


@api_bp.post("/cookie-consent")
def cookie_consent():
    payload = request.get_json(silent=True) or {}
    choice = sanitize_text(payload.get("choice"), max_length=20).lower()
    if choice not in {"accepted", "declined", "customized"}:
        return jsonify({"error": "Invalid cookie preference."}), 400

    response = jsonify({"ok": True, "choice": choice})
    response.set_cookie(
        current_app.config["COOKIE_PREFERENCE_NAME"],
        choice,
        max_age=current_app.config["COOKIE_MAX_AGE_SECONDS"],
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        httponly=False,
        samesite="Lax",
    )
    session["cookie_preference"] = choice
    session.modified = True
    return response


@api_bp.post("/chat")
def chat():
    chatbot_session = ChatbotSession(session)
    payload = request.get_json(silent=True) or {}
    message = sanitize_text(payload.get("message"), max_length=1200, preserve_newlines=True)
    if len(message) < 2:
        return jsonify({"error": "Send a short message so I can help."}), 400
    if chatbot_session.rate_limited():
        response = jsonify({"error": "Please wait a moment before sending another message."})
        response.status_code = 429
        response.headers["Retry-After"] = "20"
        return response

    duplicate = chatbot_session.duplicate_reply(message)
    if duplicate:
        history = chatbot_session.history()
        if not history or history[-1].get("text") != duplicate.reply:
            history.append({"role": "assistant", "text": duplicate.reply})
            history = chatbot_session.store_history(history)
        return jsonify(
            {
                "reply": duplicate.reply,
                "history": history,
                "provider": duplicate.provider,
                "deduplicated": True,
            }
        )

    history = chatbot_session.history()
    history.append({"role": "user", "text": message})
    session_id = session.setdefault("chat_session_id", secrets.token_urlsafe(24))
    settings = active_settings_map()
    response_text, provider = generate_gemini_reply(message, history, settings)
    response_text = sanitize_text(response_text, max_length=2000, preserve_newlines=True)
    if not response_text:
        current_app.logger.warning("Chatbot reply was empty. Falling back to a safe response.")
        response_text = "I could not respond clearly just now. Please try again, or use the Contact Us page for urgent requests."

    history.append({"role": "assistant", "text": response_text})
    history = chatbot_session.store_history(history)
    chatbot_session.remember_exchange(message, response_text, provider)

    db.session.add(
        ChatbotLog(
            session_id=session_id,
            user_message=message,
            bot_response=response_text,
            intent=classify_intent(message),
            ip_address=client_ip(),
        )
    )
    db.session.commit()
    return jsonify({"reply": response_text, "history": history, "provider": provider, "deduplicated": False})
