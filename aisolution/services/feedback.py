from __future__ import annotations

from typing import Iterable

from ..models import Feedback, Testimonial
from ..utils.security import sanitize_text


def initials_for_name(name: str) -> str:
    parts = [segment[0] for segment in (name or "").split() if segment][:2]
    value = "".join(parts).upper().strip()
    return value or "AI"


def testimonial_view(record: Testimonial) -> dict:
    return {
        "customer_name": record.customer_name,
        "company_name": record.company_name,
        "role": record.role,
        "rating": record.rating,
        "profile_image": record.profile_image,
        "feedback": record.feedback,
        "source_label": "Client testimonial",
        "avatar_label": initials_for_name(record.customer_name),
        "kind": "testimonial",
    }


def feedback_view(record: Feedback) -> dict:
    return {
        "customer_name": record.full_name,
        "company_name": "Website feedback",
        "role": "Community review",
        "rating": record.rating,
        "profile_image": "",
        "feedback": record.message,
        "source_label": "Approved feedback",
        "avatar_label": initials_for_name(record.full_name),
        "kind": "feedback",
    }


def combined_testimonials(testimonials: Iterable[Testimonial], feedback_entries: Iterable[Feedback]) -> list[dict]:
    items = [testimonial_view(record) for record in testimonials]
    items.extend(feedback_view(record) for record in feedback_entries)
    return items


def review_summary(items: Iterable[dict]) -> dict[str, str | int | float]:
    list_items = list(items)
    total = len(list_items)
    average = round(sum(float(item.get("rating", 0)) for item in list_items) / total, 1) if total else 0.0
    return {
        "total_count": total,
        "average_rating": average,
        "average_label": f"{average:.1f} / 5" if total else "0.0 / 5",
    }


def build_feedback_record(form, *, source_page: str, ip_address: str) -> Feedback:
    return Feedback(
        full_name=sanitize_text(form.full_name.data, max_length=140),
        email=(form.email.data or "").lower().strip(),
        rating=int(form.rating.data or 0),
        message=sanitize_text(form.message.data, max_length=2000, preserve_newlines=True),
        source_page=sanitize_text(source_page, max_length=120) or "home",
        ip_address=ip_address,
        active=False,
        archived=False,
        status="Pending",
    )
