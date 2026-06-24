from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from typing import Any, Sequence

from flask import current_app

from ..extensions import db
from ..models import ActivityLog
from ..utils.security import sanitize_text


@dataclass(slots=True)
class EmailDraft:
    subject: str
    recipient: str
    reply_to: str
    plain_text: str
    html_text: str | None = None
    metadata: dict[str, Any] | None = None


def _notification_target() -> str:
    return current_app.config.get("EMAIL_NOTIFICATION_TO") or current_app.config.get("ADMIN_EMAIL", "")


def _sender_address() -> str:
    return current_app.config.get("EMAIL_FROM_ADDRESS") or _notification_target()


def _sender_name() -> str:
    return current_app.config.get("EMAIL_FROM_NAME") or "AI SOLUTION"


def _smtp_mode() -> str:
    return str(current_app.config.get("EMAIL_SERVICE_MODE", "placeholder") or "placeholder").strip().lower()


def _smtp_configured() -> bool:
    return all(
        [
            current_app.config.get("EMAIL_SMTP_HOST", "").strip(),
            current_app.config.get("EMAIL_SMTP_USERNAME", "").strip(),
            current_app.config.get("EMAIL_SMTP_PASSWORD", "").strip(),
        ]
    )


def _sanitize(value: Any, *, max_length: int = 1000, preserve_newlines: bool = False) -> str:
    return sanitize_text("" if value is None else str(value), max_length=max_length, preserve_newlines=preserve_newlines)


def _field_rows(fields: Sequence[tuple[str, Any]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for label, value in fields:
        cleaned = _sanitize(value, max_length=1200, preserve_newlines=True)
        rows.append((label, cleaned or "N/A"))
    return rows


def _plain_text_email(
    heading: str,
    intro: str,
    fields: Sequence[tuple[str, str]],
    *,
    message_label: str | None = None,
    message: str | None = None,
    closing: str | None = None,
    footer: str | None = None,
) -> str:
    lines = [
        heading,
        "",
        intro,
        "",
    ]
    for label, value in fields:
        lines.append(f"{label}: {value}")
    if message_label and message:
        lines.extend(["", f"{message_label}:", message])
    if closing:
        lines.extend(["", closing])
    if footer:
        lines.extend(["", footer])
    return "\n".join(lines).strip()


def _html_email(
    heading: str,
    intro: str,
    fields: Sequence[tuple[str, str]],
    *,
    message_label: str | None = None,
    message: str | None = None,
    closing: str | None = None,
    footer: str | None = None,
) -> str:
    rows = []
    for label, value in fields:
        rows.append(
            "<tr>"
            f"<th style=\"padding:12px 0; text-align:left; vertical-align:top; width:36%; color:#7dd3fc; font-size:12px; letter-spacing:.08em; text-transform:uppercase;\">{escape(label)}</th>"
            f"<td style=\"padding:12px 0; color:#e2e8f0; font-size:15px; line-height:1.6;\">{escape(value).replace(chr(10), '<br>')}</td>"
            "</tr>"
        )

    message_block = ""
    if message_label and message:
        message_block = (
            "<div style=\"margin-top:24px; padding:18px 20px; border-radius:18px; background:rgba(15,23,42,0.92); border:1px solid rgba(125,211,252,0.18);\">"
            f"<div style=\"font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:#7dd3fc; margin-bottom:8px;\">{escape(message_label)}</div>"
            f"<div style=\"color:#f8fafc; font-size:15px; line-height:1.75; white-space:pre-line;\">{escape(message)}</div>"
            "</div>"
        )

    closing_block = ""
    if closing:
        closing_block = (
            "<div style=\"margin-top:24px; padding:18px 20px; border-left:3px solid #38bdf8; border-radius:14px; background:rgba(7,17,31,0.9); color:#dbeafe; line-height:1.7;\">"
            f"{escape(closing)}"
            "</div>"
        )

    footer_block = ""
    if footer:
        footer_block = (
            "<p style=\"margin-top:24px; font-size:12px; line-height:1.7; color:#94a3b8;\">"
            f"{escape(footer)}"
            "</p>"
        )

    return f"""
<!doctype html>
<html lang="en">
  <body style="margin:0; padding:0; background:#08111f; color:#e2e8f0; font-family:Arial, Helvetica, sans-serif;">
    <div style="max-width:680px; margin:0 auto; padding:28px 18px 36px;">
      <div style="padding:22px 24px; border-radius:24px; background:linear-gradient(180deg, rgba(14,26,45,0.98), rgba(8,16,29,0.98)); border:1px solid rgba(125,211,252,0.16); box-shadow:0 28px 60px rgba(2,6,23,0.42);">
        <div style="display:inline-flex; align-items:center; gap:10px; padding:8px 12px; border-radius:999px; background:rgba(56,189,248,0.12); color:#7dd3fc; font-size:12px; letter-spacing:.12em; text-transform:uppercase; font-weight:700;">
          {escape(_sender_name())}
        </div>
        <h1 style="margin:18px 0 10px; font-size:28px; line-height:1.25; color:#f8fafc;">{escape(heading)}</h1>
        <p style="margin:0; font-size:16px; line-height:1.75; color:#cbd5e1;">{escape(intro)}</p>
        <table style="width:100%; border-collapse:collapse; margin-top:18px;">{''.join(rows)}</table>
        {message_block}
        {closing_block}
        {footer_block}
      </div>
    </div>
  </body>
</html>
""".strip()


def _build_draft(
    *,
    subject: str,
    recipient: str,
    reply_to: str,
    heading: str,
    intro: str,
    fields: Sequence[tuple[str, Any]],
    message_label: str | None = None,
    message: str | None = None,
    closing: str | None = None,
    footer: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> EmailDraft:
    normalized_fields = _field_rows(fields)
    normalized_message = _sanitize(message, max_length=4000, preserve_newlines=True) if message else None
    plain_text = _plain_text_email(
        heading,
        intro,
        normalized_fields,
        message_label=message_label,
        message=normalized_message,
        closing=closing,
        footer=footer,
    )
    html_text = _html_email(
        heading,
        intro,
        normalized_fields,
        message_label=message_label,
        message=normalized_message,
        closing=closing,
        footer=footer,
    )
    return EmailDraft(
        subject=_sanitize(subject, max_length=255),
        recipient=_sanitize(recipient, max_length=255),
        reply_to=_sanitize(reply_to, max_length=255),
        plain_text=plain_text,
        html_text=html_text,
        metadata=metadata or {},
    )


def build_inquiry_notification_draft(inquiry, settings: dict[str, str] | None = None) -> EmailDraft:
    settings = settings or {}
    contact_email = settings.get("contact_email") or _notification_target()
    subject_value = _sanitize(getattr(inquiry, "subject", ""), max_length=180) or "General enquiry"
    service_value = _sanitize(getattr(inquiry, "service", ""), max_length=160) or "General"
    heading = f"New enquiry from {inquiry.full_name}"
    intro = f"A visitor submitted a new enquiry through the website for {service_value.lower()}."
    return _build_draft(
        subject=f"New AI SOLUTION enquiry: {subject_value}",
        recipient=contact_email,
        reply_to=inquiry.email,
        heading=heading,
        intro=intro,
        fields=[
            ("Subject", subject_value),
            ("Name", inquiry.full_name),
            ("Email", inquiry.email),
            ("Phone", inquiry.phone or "N/A"),
            ("Company", inquiry.company or "N/A"),
            ("Country", inquiry.country or "N/A"),
            ("Job Title", inquiry.job_title or "N/A"),
            ("Service", service_value),
            ("Preferred Contact Method", inquiry.contact_method or "N/A"),
            ("Budget", inquiry.budget or "N/A"),
        ],
        message_label="Message",
        message=inquiry.message,
        closing="Review the message, update the inquiry status in the admin dashboard, and reply using the visitor's preferred contact method.",
        footer="This notification was generated automatically from the AI SOLUTION website.",
        metadata={"kind": "inquiry", "source": "contact-form", "audience": "admin"},
    )


def build_inquiry_confirmation_draft(inquiry, settings: dict[str, str] | None = None) -> EmailDraft:
    settings = settings or {}
    subject_value = _sanitize(getattr(inquiry, "subject", ""), max_length=180) or "your enquiry"
    service_value = _sanitize(getattr(inquiry, "service", ""), max_length=160) or "our team"
    intro = f"Thanks for contacting AI SOLUTION. We have received your enquiry about {subject_value.lower()} and a member of our team will review it carefully."
    return _build_draft(
        subject=f"We received your AI SOLUTION enquiry: {subject_value}",
        recipient=inquiry.email,
        reply_to=current_app.config.get("EMAIL_REPLY_TO_ADDRESS") or _notification_target(),
        heading="Thank you for reaching out",
        intro=intro,
        fields=[
            ("Subject", subject_value),
            ("Service", service_value),
            ("Preferred Contact Method", inquiry.contact_method or "N/A"),
            ("Expected Next Step", "A member of our team will review the message and respond within one business day."),
        ],
        closing="If you need to add anything urgent, simply reply to this email and our team will pick it up.",
        footer="This is an automated confirmation from AI SOLUTION.",
        metadata={"kind": "inquiry", "source": "contact-form", "audience": "user"},
    )


def build_feedback_notification_draft(feedback, settings: dict[str, str] | None = None) -> EmailDraft:
    settings = settings or {}
    contact_email = settings.get("contact_email") or _notification_target()
    source_page = _sanitize(getattr(feedback, "source_page", ""), max_length=120) or "home"
    rating_value = f"{int(getattr(feedback, 'rating', 0) or 0)}/5"
    heading = f"New feedback from {feedback.full_name}"
    intro = "A visitor submitted feedback through the website feedback form."
    return _build_draft(
        subject=f"New AI SOLUTION feedback: {feedback.full_name} ({rating_value})",
        recipient=contact_email,
        reply_to=feedback.email,
        heading=heading,
        intro=intro,
        fields=[
            ("Name", feedback.full_name),
            ("Email", feedback.email),
            ("Rating", rating_value),
            ("Source Page", source_page),
        ],
        message_label="Feedback",
        message=feedback.message,
        closing="Review the submission in the admin dashboard and publish it when it is ready for public display.",
        footer="This notification was generated automatically from the AI SOLUTION website.",
        metadata={"kind": "feedback", "source": "homepage-modal", "audience": "admin"},
    )


def build_feedback_confirmation_draft(feedback, settings: dict[str, str] | None = None) -> EmailDraft:
    source_page = _sanitize(getattr(feedback, "source_page", ""), max_length=120) or "home"
    rating_value = f"{int(getattr(feedback, 'rating', 0) or 0)}/5"
    intro = "Thank you for taking the time to share feedback with AI SOLUTION. Your message has been received and will be reviewed before publication."
    return _build_draft(
        subject="Thanks for sharing feedback with AI SOLUTION",
        recipient=feedback.email,
        reply_to=current_app.config.get("EMAIL_REPLY_TO_ADDRESS") or _notification_target(),
        heading="We received your feedback",
        intro=intro,
        fields=[
            ("Rating", rating_value),
            ("Source Page", source_page),
            ("Review Timeline", "We usually review submissions before they are published on the website."),
        ],
        closing="If you want to add context, you can reply to this email and our team will update the review notes.",
        footer="This is an automated confirmation from AI SOLUTION.",
        metadata={"kind": "feedback", "source": "homepage-modal", "audience": "user"},
    )


def build_rsvp_notification_draft(rsvp, event, settings: dict[str, str] | None = None) -> EmailDraft:
    settings = settings or {}
    contact_email = settings.get("contact_email") or _notification_target()
    heading = f"New RSVP for {event.title}"
    intro = "An event registration was submitted through the public events page."
    return _build_draft(
        subject=f"New AI SOLUTION RSVP: {event.title} - {rsvp.full_name}",
        recipient=contact_email,
        reply_to=rsvp.email,
        heading=heading,
        intro=intro,
        fields=[
            ("Event", event.title),
            ("Date", f"{event.event_date:%b %d, %Y}"),
            ("Time", event.event_time),
            ("Location", event.location),
            ("Name", rsvp.full_name),
            ("Email", rsvp.email),
            ("Phone", rsvp.phone or "N/A"),
            ("Company", rsvp.company or "N/A"),
            ("Job Title", rsvp.job_title or "N/A"),
            ("Attendees", str(rsvp.attendees or 1)),
            ("Preferred Session", rsvp.preferred_session or "N/A"),
        ],
        message_label="Special Requirements",
        message=rsvp.special_requirements or "",
        closing="Confirm the registration in the admin dashboard and share the event details with the attendee.",
        footer="This notification was generated automatically from the AI SOLUTION website.",
        metadata={"kind": "rsvp", "source": "events-page", "audience": "admin"},
    )


def build_rsvp_confirmation_draft(rsvp, event, settings: dict[str, str] | None = None) -> EmailDraft:
    intro = f"Thanks for registering for {event.title}. Your RSVP has been confirmed and we will send the final event details shortly."
    return _build_draft(
        subject=f"Your RSVP is confirmed: {event.title}",
        recipient=rsvp.email,
        reply_to=current_app.config.get("EMAIL_REPLY_TO_ADDRESS") or _notification_target(),
        heading="Your event seat is reserved",
        intro=intro,
        fields=[
            ("Event", event.title),
            ("Date", f"{event.event_date:%b %d, %Y}"),
            ("Time", event.event_time),
            ("Location", event.location),
            ("Attendees", str(rsvp.attendees or 1)),
            ("Preferred Session", rsvp.preferred_session or "N/A"),
        ],
        closing="If your plans change, reply to this email and we will update the registration notes.",
        footer="This is an automated confirmation from AI SOLUTION.",
        metadata={"kind": "rsvp", "source": "events-page", "audience": "user"},
    )


def build_application_notification_draft(application, settings: dict[str, str] | None = None) -> EmailDraft:
    settings = settings or {}
    contact_email = settings.get("contact_email") or _notification_target()
    heading = f"New application for {application.position}"
    intro = "A career application was submitted through the public careers page."
    return _build_draft(
        subject=f"New AI SOLUTION application: {application.position} - {application.full_name}",
        recipient=contact_email,
        reply_to=application.email,
        heading=heading,
        intro=intro,
        fields=[
            ("Position", application.position),
            ("Name", application.full_name),
            ("Email", application.email),
            ("Phone", application.phone),
            ("Address", application.address),
            ("Experience", application.experience),
            ("Portfolio URL", application.portfolio_url or "N/A"),
            ("Resume File", application.original_resume_name),
        ],
        message_label="Cover Letter",
        message=application.cover_letter,
        closing="Review the application in the admin dashboard and continue the hiring workflow if the role remains open.",
        footer="This notification was generated automatically from the AI SOLUTION website.",
        metadata={"kind": "application", "source": "careers-page", "audience": "admin"},
    )


def build_application_confirmation_draft(application, settings: dict[str, str] | None = None) -> EmailDraft:
    intro = f"Thanks for applying for the {application.position} role at AI SOLUTION. We have received your application and will review it carefully."
    return _build_draft(
        subject=f"We received your application for {application.position}",
        recipient=application.email,
        reply_to=current_app.config.get("EMAIL_REPLY_TO_ADDRESS") or _notification_target(),
        heading="Application received",
        intro=intro,
        fields=[
            ("Position", application.position),
            ("Experience", application.experience),
            ("Review Timeline", "Our hiring team reviews applications carefully and will contact you if there is a fit."),
        ],
        closing="If you need to update any details, reply to this email and our team will note the change.",
        footer="This is an automated confirmation from AI SOLUTION.",
        metadata={"kind": "application", "source": "careers-page", "audience": "user"},
    )


def build_newsletter_notification_draft(email: str, settings: dict[str, str] | None = None) -> EmailDraft:
    settings = settings or {}
    contact_email = settings.get("contact_email") or _notification_target()
    normalized_email = _sanitize(email, max_length=255)
    return _build_draft(
        subject=f"New AI SOLUTION newsletter subscriber: {normalized_email}",
        recipient=contact_email,
        reply_to=normalized_email,
        heading="New newsletter subscription",
        intro="A visitor subscribed to the AI SOLUTION newsletter through the website footer form.",
        fields=[
            ("Email", normalized_email),
            ("Source", "Website footer"),
        ],
        closing="Keep the subscriber list updated in the admin dashboard and activate the next campaign when ready.",
        footer="This notification was generated automatically from the AI SOLUTION website.",
        metadata={"kind": "newsletter", "source": "footer-form", "audience": "admin"},
    )


def build_newsletter_confirmation_draft(email: str, settings: dict[str, str] | None = None) -> EmailDraft:
    normalized_email = _sanitize(email, max_length=255)
    intro = "Thanks for subscribing to AI SOLUTION insights. You will receive updates on delivery stories, events, and practical AI guidance."
    return _build_draft(
        subject="You're subscribed to AI SOLUTION insights",
        recipient=normalized_email,
        reply_to=current_app.config.get("EMAIL_REPLY_TO_ADDRESS") or _notification_target(),
        heading="Welcome to the AI SOLUTION newsletter",
        intro=intro,
        fields=[
            ("Email", normalized_email),
            ("Preference", "You can unsubscribe at any time from future messages."),
        ],
        closing="If you ever need help, reply to this email and our team will point you to the right page.",
        footer="This is an automated confirmation from AI SOLUTION.",
        metadata={"kind": "newsletter", "source": "footer-form", "audience": "user"},
    )

def build_inquiry_email_draft(inquiry, settings: dict[str, str] | None = None) -> EmailDraft:
    return build_inquiry_notification_draft(inquiry, settings)


def build_feedback_email_draft(feedback, settings: dict[str, str] | None = None) -> EmailDraft:
    return build_feedback_notification_draft(feedback, settings)


def _smtp_message(draft: EmailDraft) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = draft.subject
    message["From"] = formataddr((_sender_name(), _sender_address()))
    message["To"] = draft.recipient
    if draft.reply_to:
        message["Reply-To"] = draft.reply_to
    message.set_content(draft.plain_text)
    if draft.html_text:
        message.add_alternative(draft.html_text, subtype="html")
    return message


def _record_email_delivery(draft: EmailDraft, result: dict[str, Any]) -> None:
    metadata = draft.metadata or {}
    action = "email-preview" if result.get("mode") == "preview" else "email-delivered" if result.get("ok") else "email-failed"
    description = (
        f"{metadata.get('kind', 'email')} {result.get('mode', 'unknown')} message for {draft.recipient} "
        f"with subject {draft.subject!r}."
    )
    try:
        db.session.add(
            ActivityLog(
                actor_type="system",
                actor_name="Email Service",
                action=action,
                resource_type=str(metadata.get("kind") or "email"),
                resource_id=draft.recipient,
                description=description,
                ip_address="",
                user_agent="",
                details={
                    "recipient": draft.recipient,
                    "subject": draft.subject,
                    "mode": result.get("mode"),
                    "delivered": bool(result.get("delivered")),
                    "provider": result.get("provider", ""),
                    "source": metadata.get("source", ""),
                    "audience": metadata.get("audience", ""),
                },
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.debug("Email delivery log could not be persisted.", exc_info=True)


def send_email_draft(draft: EmailDraft) -> dict[str, Any]:
    mode = _smtp_mode()
    result: dict[str, Any]

    if mode in {"placeholder", "preview", "log"}:
        current_app.logger.info(
            "Prepared %s email draft for %s with subject %r.",
            mode,
            draft.recipient,
            draft.subject,
        )
        result = {
            "ok": True,
            "delivered": False,
            "mode": "preview",
            "provider": "preview",
            "recipient": draft.recipient,
            "subject": draft.subject,
        }
        _record_email_delivery(draft, result)
        return result

    if not _smtp_configured():
        current_app.logger.warning(
            "SMTP delivery was requested for %s but the Gmail configuration is incomplete.",
            draft.recipient,
        )
        result = {
            "ok": False,
            "delivered": False,
            "mode": "smtp",
            "provider": "gmail-smtp",
            "recipient": draft.recipient,
            "subject": draft.subject,
            "error": "SMTP credentials are not configured.",
        }
        _record_email_delivery(draft, result)
        return result

    host = current_app.config.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port = int(current_app.config.get("EMAIL_SMTP_PORT", 587))
    timeout = int(current_app.config.get("EMAIL_SMTP_TIMEOUT_SECONDS", 20))
    use_tls = bool(current_app.config.get("EMAIL_SMTP_USE_TLS", True))
    use_ssl = bool(current_app.config.get("EMAIL_SMTP_USE_SSL", False))
    username = current_app.config.get("EMAIL_SMTP_USERNAME", "").strip()
    password = current_app.config.get("EMAIL_SMTP_PASSWORD", "")

    try:
        message = _smtp_message(draft)
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        current_app.logger.info("Delivered email to %s with subject %r via Gmail SMTP.", draft.recipient, draft.subject)
        result = {
            "ok": True,
            "delivered": True,
            "mode": "smtp",
            "provider": "gmail-smtp",
            "recipient": draft.recipient,
            "subject": draft.subject,
        }
    except Exception as exc:
        current_app.logger.exception("Email delivery failed for %s with subject %r.", draft.recipient, draft.subject)
        result = {
            "ok": False,
            "delivered": False,
            "mode": "smtp",
            "provider": "gmail-smtp",
            "recipient": draft.recipient,
            "subject": draft.subject,
            "error": str(exc),
        }

    _record_email_delivery(draft, result)
    return result


def preview_email_delivery(draft: EmailDraft) -> dict[str, Any]:
    return send_email_draft(draft)
