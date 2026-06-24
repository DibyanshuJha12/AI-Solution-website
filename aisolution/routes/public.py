from __future__ import annotations

import secrets
from datetime import timedelta
from functools import wraps
from math import ceil
from html import escape
from urllib.parse import quote_plus

from flask import Blueprint, Response, abort, current_app, flash, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy import func

from ..data import EVENTS as EVENT_BLUEPRINTS, PREVIOUS_EVENTS
from ..extensions import db
from ..forms import (
    ApplicationForm,
    ClientLoginForm,
    ClientRegistrationForm,
    ForgotPasswordForm,
    FeedbackForm,
    InquiryForm,
    NewsletterForm,
    ResetPasswordForm,
    RSVPForm,
)
from ..models import (
    ActivityLog,
    Application,
    AuthSessionLog,
    BlogPost,
    CaseStudy,
    ChatbotLog,
    Event,
    FaqItem,
    Feedback,
    Industry,
    Inquiry,
    Job,
    NewsletterSubscriber,
    PasswordResetToken,
    PublicUser,
    RSVP,
    Service,
    SiteSetting,
    TeamMember,
    Testimonial,
    utcnow,
)
from ..services.feedback import build_feedback_record, combined_testimonials, review_summary
from ..utils.security import (
    allowed_file,
    build_numeric_captcha,
    client_ip,
    create_session_identifier,
    hash_token,
    is_login_rate_limited,
    is_suspicious_login,
    parse_user_agent,
    sanitize_text,
    secure_resume_filename,
    verify_numeric_captcha,
    verify_recaptcha_token,
)
from ..utils.site import active_settings_map


public_bp = Blueprint("public", __name__)
SESSION_PRESERVE_KEYS = ("cookie_preference",)


def recaptcha_action(scope: str) -> str:
    return "".join(character if character.isalnum() or character in {"_", "/"} else "_" for character in scope) or "submit"


def reset_public_session(values: dict | None = None, *, permanent: bool | None = None) -> None:
    preserved = {key: session.get(key) for key in SESSION_PRESERVE_KEYS if key in session}
    session.clear()
    session.update(preserved)
    if values:
        session.update(values)
    if permanent is not None:
        session.permanent = permanent


def client_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("public_user_id")
        if not user_id:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("public.login"))
        user = db.session.get(PublicUser, user_id)
        if not user or not user.is_active:
            reset_public_session()
            flash("Your session has ended. Please sign in again.", "error")
            return redirect(url_for("public.login"))
        g.public_user = user
        return view(*args, **kwargs)

    return wrapped


def active_services():
    return Service.query.filter_by(active=True, archived=False)


def active_events():
    return Event.query.filter_by(active=True, archived=False)


def active_jobs():
    return Job.query.filter_by(active=True, archived=False)


def service_choices() -> list[tuple[str, str]]:
    services = active_services().order_by(Service.title.asc()).all()
    return [(service.title, service.title) for service in services]


def event_choices() -> list[tuple[int, str]]:
    events = active_events().order_by(Event.event_date.asc()).all()
    return [(event.id, f"{event.title} - {event.event_date:%b %d, %Y}") for event in events]


def event_showcase_cards(events: list[Event]) -> list[dict]:
    cards: list[dict] = []
    for index, event in enumerate(events):
        blueprint = EVENT_BLUEPRINTS[index % len(EVENT_BLUEPRINTS)] if EVENT_BLUEPRINTS else {}
        cards.append(
            {
                "id": event.id,
                "title": event.title,
                "banner_image": event.banner_image,
                "event_date": event.event_date,
                "event_time": event.event_time,
                "location": event.location,
                "details": event.details,
                "category": blueprint.get("category", "AI Program"),
                "icon": blueprint.get("icon", "calendar-days"),
                "format_label": blueprint.get("format_label", "Innovation Session"),
            }
        )
    return cards


def job_choices() -> list[tuple[str, str]]:
    jobs = active_jobs().order_by(Job.title.asc()).all()
    return [(job.title, job.title) for job in jobs]


def prepare_captcha(form, scope: str) -> str:
    form.captcha_scope.data = scope
    return build_numeric_captcha(scope)["prompt"]


def verify_form_captcha(form, default_scope: str) -> bool:
    verified, message = verify_numeric_captcha(form.captcha_scope.data or default_scope, form.captcha_answer.data)
    if not verified:
        flash(message, "error")
        return False
    recaptcha_verified, recaptcha_message = verify_recaptcha_token(
        getattr(form, "recaptcha_token", None).data if hasattr(form, "recaptcha_token") else None,
        action=recaptcha_action(default_scope),
    )
    if not recaptcha_verified:
        flash(recaptcha_message, "error")
        return False
    return True


def log_public_activity(action: str, resource_type: str, description: str, *, resource_id: str | None = None) -> None:
    public_user_id = session.get("public_user_id")
    user = db.session.get(PublicUser, public_user_id) if public_user_id else None
    db.session.add(
        ActivityLog(
            actor_type="public",
            actor_name=user.full_name if user else "Visitor",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            description=description,
            ip_address=client_ip(),
            user_agent=(request.user_agent.string or "")[:300],
            public_user_id=user.id if user else None,
            details={},
        )
    )


def record_public_auth_event(
    *,
    email: str,
    success: bool,
    session_identifier: str,
    public_user: PublicUser | None = None,
    suspicious: bool = False,
    failure_reason: str | None = None,
) -> AuthSessionLog:
    agent = parse_user_agent(request.user_agent.string or "")
    event = AuthSessionLog(
        user_type="public",
        email=email.lower().strip(),
        success=success,
        suspicious=suspicious,
        failure_reason=failure_reason,
        session_identifier=session_identifier,
        ip_address=client_ip(),
        user_agent=(request.user_agent.string or "")[:300],
        browser=agent["browser"],
        device=agent["device"],
        operating_system=agent["operating_system"],
        public_user_id=public_user.id if public_user else None,
    )
    db.session.add(event)
    return event


def prepare_inquiry_form() -> InquiryForm:
    form = InquiryForm()
    form.service.choices = service_choices()
    selected_service = request.args.get("service")
    if selected_service and not form.service.data:
        form.service.data = selected_service
    selected_subject = request.args.get("subject")
    if selected_subject and not form.subject.data:
        form.subject.data = selected_subject
    elif form.service.data and not form.subject.data:
        form.subject.data = f"{form.service.data} enquiry"
    return form


def approved_feedback_query():
    return Feedback.query.filter_by(active=True, archived=False, status="Approved")


def safe_active_settings_map() -> dict[str, str]:
    try:
        return active_settings_map()
    except Exception:
        current_app.logger.debug("Site settings unavailable for public contact rendering.", exc_info=True)
        return {}


def normalise_timestamp(value):
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is None:
        return value.replace(tzinfo=utcnow().tzinfo)
    return value


def masked_email(email: str) -> str:
    if "@" not in email:
        return email
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        local_part = local_part[:1] + "***"
    else:
        local_part = local_part[:2] + "***"
    return f"{local_part}@{domain}"


def duplicate_inquiry_exists(*, email: str, subject: str, service: str, message: str, window_minutes: int) -> bool:
    cutoff = utcnow() - timedelta(minutes=window_minutes)
    duplicate = (
        Inquiry.query.filter(
            func.lower(Inquiry.email) == email.lower().strip(),
            func.lower(func.coalesce(Inquiry.subject, "")) == subject.lower().strip(),
            func.lower(func.coalesce(Inquiry.service, "")) == service.lower().strip(),
            func.lower(func.coalesce(Inquiry.message, "")) == message.lower().strip(),
        )
        .order_by(Inquiry.created_at.desc())
        .first()
    )
    duplicate_created_at = normalise_timestamp(duplicate.created_at) if duplicate else None
    return bool(duplicate_created_at and duplicate_created_at >= cutoff)


def duplicate_feedback_exists(*, email: str, message: str, window_minutes: int) -> bool:
    cutoff = utcnow() - timedelta(minutes=window_minutes)
    duplicate = (
        Feedback.query.filter(
            func.lower(Feedback.email) == email.lower().strip(),
            func.lower(func.coalesce(Feedback.message, "")) == message.lower().strip(),
        )
        .order_by(Feedback.created_at.desc())
        .first()
    )
    duplicate_created_at = normalise_timestamp(duplicate.created_at) if duplicate else None
    return bool(duplicate_created_at and duplicate_created_at >= cutoff)


def site_map_entries() -> list[tuple[str, dict[str, str]]]:
    entries: list[tuple[str, dict[str, str]]] = [
        ("public.home", {}),
        ("public.solutions", {}),
        ("public.portfolio", {}),
        ("public.testimonials", {}),
        ("public.events", {}),
        ("public.blog", {}),
        ("public.careers", {}),
        ("public.contact", {}),
        ("public.privacy", {}),
        ("public.terms", {}),
    ]
    for post in BlogPost.query.filter_by(active=True, archived=False).order_by(BlogPost.publish_date.desc()).all():
        entries.append(("public.blog_detail", {"slug": post.slug}))
    return entries


@public_bp.route("/")
def home():
    services = active_services().limit(4).all()
    testimonial_query = Testimonial.query.filter_by(active=True, archived=False).order_by(Testimonial.id.asc())
    feedback_query = approved_feedback_query().order_by(Feedback.created_at.desc())
    testimonial_count = testimonial_query.count()
    approved_feedback_count = feedback_query.count()
    review_cards = combined_testimonials(testimonial_query.limit(4).all(), feedback_query.limit(4).all())
    review_stats = review_summary(
        combined_testimonials(testimonial_query.all(), feedback_query.all())
    )
    blogs = BlogPost.query.filter_by(active=True, archived=False).order_by(BlogPost.publish_date.desc()).limit(3).all()
    events = active_events().order_by(Event.event_date.asc()).limit(3).all()
    team_members = TeamMember.query.filter_by(active=True, archived=False).order_by(TeamMember.sort_order.asc()).all()
    faqs = FaqItem.query.filter_by(active=True, archived=False).order_by(FaqItem.sort_order.asc()).all()
    return render_template(
        "home.html",
        services=services,
        testimonials=review_cards,
        blogs=blogs,
        events=events,
        team_members=team_members,
        faqs=faqs,
        testimonial_count=testimonial_count,
        approved_feedback_count=approved_feedback_count,
        review_stats=review_stats,
        stats=[
            ("72", "AI workflows shipped"),
            ("41%", "Average process acceleration"),
            ("18", "Industries supported"),
            ("99%", "Target platform uptime"),
        ],
    )


@public_bp.route("/solutions")
def solutions():
    services = active_services().order_by(Service.category.asc(), Service.title.asc()).all()
    industries = Industry.query.filter_by(active=True, archived=False).order_by(Industry.id.asc()).all()
    categories = sorted({service.category for service in services})
    return render_template("solutions.html", services=services, industries=industries, categories=categories)


@public_bp.route("/industries")
def industries():
    return redirect(url_for("public.solutions", _anchor="industries"))


@public_bp.route("/portfolio")
def portfolio():
    cases = CaseStudy.query.filter_by(active=True, archived=False).order_by(CaseStudy.id.asc()).all()
    return render_template("portfolio.html", cases=cases)


@public_bp.route("/media/<path:filename>")
def uploaded_media(filename: str):
    return send_from_directory(current_app.config["MEDIA_UPLOAD_FOLDER"], filename)


@public_bp.route("/testimonials")
def testimonials():
    testimonial_query = Testimonial.query.filter_by(active=True, archived=False).order_by(Testimonial.id.asc())
    feedback_query = approved_feedback_query().order_by(Feedback.created_at.desc())
    items = combined_testimonials(testimonial_query.all(), feedback_query.all())
    summary = review_summary(items)
    return render_template(
        "testimonials.html",
        testimonials=items,
        review_stats=summary,
        testimonial_count=testimonial_query.count(),
        approved_feedback_count=feedback_query.count(),
    )


@public_bp.route("/events", methods=["GET", "POST"])
def events():
    events_list = active_events().order_by(Event.event_date.asc()).all()
    showcase_events = event_showcase_cards(events_list)
    featured_event = showcase_events[0] if showcase_events else None
    form = RSVPForm()
    form.event_id.choices = event_choices()
    captcha_prompt = prepare_captcha(form, "event-rsvp")
    if request.method == "GET" and request.args.get("event"):
        try:
            form.event_id.data = int(request.args["event"])
        except ValueError:
            pass

    if form.validate_on_submit():
        verified, captcha_message = verify_numeric_captcha(form.captcha_scope.data or "event-rsvp", form.captcha_answer.data)
        if not verified:
            form.captcha_answer.errors.append(captcha_message)
            flash("Please correct the highlighted RSVP fields and try again.", "error")
            return render_template(
                "events.html",
                showcase_events=showcase_events,
                featured_event=featured_event,
                form=form,
                captcha_prompt=prepare_captcha(form, "event-rsvp"),
            )
        recaptcha_verified, recaptcha_message = verify_recaptcha_token(form.recaptcha_token.data, action=recaptcha_action("event-rsvp"))
        if not recaptcha_verified:
            form.captcha_answer.errors.append(recaptcha_message)
            flash("Please complete the security verification and try again.", "error")
            return render_template(
                "events.html",
                showcase_events=showcase_events,
                featured_event=featured_event,
                form=form,
                captcha_prompt=prepare_captcha(form, "event-rsvp"),
            )

        normalized_email = form.email.data.lower().strip()
        duplicate_cutoff = utcnow() - timedelta(minutes=10)
        recent_duplicate = (
            RSVP.query.filter(
                RSVP.event_id == form.event_id.data,
                func.lower(RSVP.email) == normalized_email,
            )
            .order_by(RSVP.created_at.desc())
            .first()
        )
        recent_duplicate_created_at = recent_duplicate.created_at if recent_duplicate else None
        if recent_duplicate_created_at and recent_duplicate_created_at.tzinfo is None:
            recent_duplicate_created_at = recent_duplicate_created_at.replace(tzinfo=duplicate_cutoff.tzinfo)

        if recent_duplicate_created_at and recent_duplicate_created_at >= duplicate_cutoff:
            flash("We already received this RSVP recently. Please wait a moment before trying again.", "error")
            return redirect(url_for("public.events", _anchor="rsvp"))

        rsvp = RSVP(
            event_id=form.event_id.data,
            full_name=sanitize_text(form.full_name.data, max_length=160),
            email=normalized_email,
            phone=sanitize_text(form.phone.data, max_length=60),
            company=sanitize_text(form.company.data, max_length=160),
            job_title=sanitize_text(form.job_title.data, max_length=120),
            attendees=form.attendees.data,
            preferred_session=sanitize_text(form.preferred_session.data, max_length=120),
            special_requirements=sanitize_text(form.special_requirements.data, max_length=800, preserve_newlines=True),
            message=sanitize_text(form.message.data, max_length=1500, preserve_newlines=True),
        )
        db.session.add(rsvp)
        log_public_activity("create", "rsvp", f"Created RSVP for {rsvp.email}.")
        db.session.commit()
        flash("Your RSVP is confirmed. We will review the details and follow up soon.", "success")
        return redirect(url_for("public.events"))
    elif request.method == "POST":
        flash("Please correct the highlighted RSVP fields and try again.", "error")

    return render_template(
        "events.html",
        showcase_events=showcase_events,
        featured_event=featured_event,
        previous_events=PREVIOUS_EVENTS[:4],
        form=form,
        captcha_prompt=captcha_prompt,
    )


@public_bp.route("/blog")
def blog():
    posts = BlogPost.query.filter_by(active=True, archived=False).order_by(BlogPost.publish_date.desc()).all()
    for post in posts:
        post.read_time = max(3, ceil(len((post.content or "").split()) / 190)) if (post.content or "").strip() else 3
    return render_template("blog.html", posts=posts)


@public_bp.route("/blog/<slug>")
def blog_detail(slug: str):
    post = BlogPost.query.filter_by(slug=slug, active=True, archived=False).first_or_404()
    related_posts = (
        BlogPost.query.filter(BlogPost.id != post.id, BlogPost.active.is_(True), BlogPost.archived.is_(False))
        .order_by(BlogPost.publish_date.desc())
        .limit(3)
        .all()
    )
    word_count = len((post.content or "").split())
    read_time = max(3, ceil(word_count / 190)) if word_count else 3
    share_url = request.url
    share_title = post.title
    share_links = {
        "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={quote_plus(share_url)}",
        "x": f"https://twitter.com/intent/tweet?text={quote_plus(share_title)}&url={quote_plus(share_url)}",
    }
    sample_comments = [
        {
            "name": "Operations Lead",
            "role": "Enterprise Delivery Team",
            "body": "This breakdown is useful because it keeps governance and rollout planning in the same conversation rather than treating them as separate workstreams.",
        },
        {
            "name": "Technology Director",
            "role": "AI Programme Sponsor",
            "body": "The practical framing around adoption and measurable outcomes is exactly what most teams need before moving from prototype to production.",
        },
        {
            "name": "Service Transformation Manager",
            "role": "Customer Operations",
            "body": "Strong article. The link between workflow design and trust is often missed, and that is where most enterprise AI programmes succeed or stall.",
        },
    ]
    return render_template(
        "blog_detail.html",
        post=post,
        related_posts=related_posts,
        read_time=read_time,
        share_links=share_links,
        sample_comments=sample_comments,
    )


@public_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("public_user_id"):
        return redirect(url_for("public.workspace"))

    login_form = ClientLoginForm(prefix="login")
    register_form = ClientRegistrationForm(prefix="register")
    forgot_form = ForgotPasswordForm(prefix="forgot")
    captcha_login = prepare_captcha(login_form, "public-login")
    captcha_register = prepare_captcha(register_form, "public-register")
    captcha_forgot = prepare_captcha(forgot_form, "public-forgot")
    active_panel = request.args.get("panel", "login")
    reset_preview_url = None

    if request.method == "POST":
        form_name = request.form.get("form_name", "login")
        active_panel = form_name

        if form_name == "login":
            if login_form.validate():
                email = login_form.email.data.lower().strip()
                if is_login_rate_limited(email, "public"):
                    flash("Too many failed attempts. Please wait before trying again.", "error")
                    return redirect(url_for("public.login", panel="login"))
                if not verify_form_captcha(login_form, "public-login"):
                    return redirect(url_for("public.login", panel="login"))

                user = PublicUser.query.filter(func.lower(PublicUser.email) == email).first()
                session_identifier = create_session_identifier()
                agent = parse_user_agent(request.user_agent.string or "")
                suspicious = is_suspicious_login(email, "public", client_ip(), agent["browser"], agent["operating_system"])
                if not user or not user.is_active or not user.check_password(login_form.password.data):
                    if user:
                        user.failed_login_count += 1
                    record_public_auth_event(
                        email=email,
                        success=False,
                        session_identifier=session_identifier,
                        failure_reason="Invalid credentials",
                        suspicious=suspicious,
                    )
                    db.session.commit()
                    flash("Invalid credentials or inactive account.", "error")
                    return redirect(url_for("public.login", panel="login"))

                user.last_login_at = utcnow()
                user.last_login_ip = client_ip()
                user.failed_login_count = 0
                auth_event = record_public_auth_event(
                    email=email,
                    success=True,
                    session_identifier=session_identifier,
                    public_user=user,
                    suspicious=suspicious,
                )
                db.session.flush()
                reset_public_session(
                    {
                        "public_user_id": user.id,
                        "public_session_identifier": session_identifier,
                        "public_session_log_id": auth_event.id,
                    },
                    permanent=bool(login_form.remember.data),
                )
                db.session.add(
                    ActivityLog(
                        actor_type="public",
                        actor_name=user.full_name,
                        action="login",
                        resource_type="auth",
                        resource_id=str(user.id),
                        description="Client user signed in.",
                        ip_address=client_ip(),
                        user_agent=(request.user_agent.string or "")[:300],
                        public_user_id=user.id,
                        details={"suspicious": suspicious},
                    )
                )
                db.session.commit()
                flash("Welcome back. Your secure workspace is ready.", "success")
                return redirect(url_for("public.workspace"))

        elif form_name == "register":
            if register_form.validate():
                email = register_form.email.data.lower().strip()
                if not verify_form_captcha(register_form, "public-register"):
                    return redirect(url_for("public.login", panel="register"))
                if PublicUser.query.filter(func.lower(PublicUser.email) == email).first():
                    flash("An account with that email already exists.", "error")
                    return redirect(url_for("public.login", panel="register"))

                user = PublicUser(
                    full_name=sanitize_text(register_form.full_name.data, max_length=160),
                    company=sanitize_text(register_form.company.data, max_length=160),
                    email=email,
                    accepted_privacy=True,
                    accepted_privacy_at=utcnow(),
                    is_active=True,
                    last_login_at=utcnow(),
                    last_login_ip=client_ip(),
                )
                user.set_password(register_form.password.data)
                db.session.add(user)
                db.session.flush()
                session_identifier = create_session_identifier()
                auth_event = record_public_auth_event(
                    email=email,
                    success=True,
                    session_identifier=session_identifier,
                    public_user=user,
                )
                db.session.flush()
                reset_public_session(
                    {
                        "public_user_id": user.id,
                        "public_session_identifier": session_identifier,
                        "public_session_log_id": auth_event.id,
                    },
                    permanent=bool(register_form.remember.data),
                )
                db.session.add(
                    ActivityLog(
                        actor_type="public",
                        actor_name=user.full_name,
                        action="register",
                        resource_type="account",
                        resource_id=str(user.id),
                        description="Client user created an account.",
                        ip_address=client_ip(),
                        user_agent=(request.user_agent.string or "")[:300],
                        public_user_id=user.id,
                        details={},
                    )
                )
                db.session.commit()
                flash("Account created successfully.", "success")
                return redirect(url_for("public.workspace"))

        elif form_name == "forgot":
            if forgot_form.validate():
                if not verify_form_captcha(forgot_form, "public-forgot"):
                    return redirect(url_for("public.login", panel="forgot"))
                email = forgot_form.email.data.lower().strip()
                user = PublicUser.query.filter(func.lower(PublicUser.email) == email).first()
                if user and user.is_active:
                    raw_token = secrets.token_urlsafe(32)
                    token = PasswordResetToken(
                        public_user_id=user.id,
                        token_hash=hash_token(raw_token),
                        expires_at=PasswordResetToken.default_expiry(),
                        request_ip=client_ip(),
                    )
                    db.session.add(token)
                    db.session.flush()
                    if current_app.config.get("EXPOSE_RESET_LINKS_IN_DEBUG") and current_app.debug:
                        reset_preview_url = url_for("public.reset_password", token=raw_token, _external=False)
                flash("If an account exists for that email, a reset path has been generated securely.", "success")
                db.session.commit()
            else:
                flash("Please correct the highlighted reset request fields.", "error")

    return render_template(
        "login.html",
        login_form=login_form,
        register_form=register_form,
        forgot_form=forgot_form,
        captcha_login=captcha_login,
        captcha_register=captcha_register,
        captcha_forgot=captcha_forgot,
        active_panel=active_panel,
        reset_preview_url=reset_preview_url,
    )


@public_bp.route("/login/reset/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    hashed = hash_token(token)
    reset_record = PasswordResetToken.query.filter_by(token_hash=hashed).first_or_404()
    if not reset_record.is_valid:
        flash("This password reset link is invalid or has expired.", "error")
        return redirect(url_for("public.login", panel="forgot"))

    form = ResetPasswordForm()
    captcha_prompt = prepare_captcha(form, "public-reset")
    if form.validate_on_submit():
        if not verify_form_captcha(form, "public-reset"):
            return redirect(url_for("public.reset_password", token=token))
        user = db.session.get(PublicUser, reset_record.public_user_id) or abort(404)
        user.set_password(form.password.data)
        user.failed_login_count = 0
        reset_record.used_at = utcnow()
        log_public_activity("password-reset", "account", f"Password reset completed for {user.email}.", resource_id=str(user.id))
        db.session.commit()
        flash("Your password has been updated. Please sign in.", "success")
        return redirect(url_for("public.login", panel="login"))

    return render_template("reset_password.html", form=form, token=token, captcha_prompt=captcha_prompt)


@public_bp.route("/logout")
@client_required
def logout():
    session_log_id = session.get("public_session_log_id")
    if session_log_id:
        auth_event = db.session.get(AuthSessionLog, session_log_id)
        if auth_event and not auth_event.logged_out_at:
            auth_event.logged_out_at = utcnow()
    log_public_activity("logout", "auth", "Client user signed out.")
    db.session.commit()
    reset_public_session()
    flash("You have been signed out.", "success")
    return redirect(url_for("public.login"))


@public_bp.route("/workspace")
@client_required
def workspace():
    user = g.public_user
    inquiry_count = Inquiry.query.filter(func.lower(Inquiry.email) == user.email.lower()).count()
    chatbot_count = ChatbotLog.query.filter_by(ip_address=client_ip()).count()
    return render_template("client_dashboard.html", user=user, inquiry_count=inquiry_count, chatbot_count=chatbot_count)


@public_bp.route("/careers", methods=["GET", "POST"])
def careers():
    jobs = active_jobs().order_by(Job.department.asc(), Job.title.asc()).all()
    form = ApplicationForm()
    form.position.choices = job_choices()
    captcha_prompt = prepare_captcha(form, "career-apply")
    selected_position = request.args.get("position")
    if request.method == "GET" and selected_position:
        form.position.data = selected_position

    if form.validate_on_submit():
        if not verify_form_captcha(form, "career-apply"):
            return redirect(url_for("public.careers", _anchor="apply"))

        uploaded = form.resume.data
        if not uploaded or not allowed_file(uploaded.filename):
            flash("Upload a PDF, DOC, or DOCX resume.", "error")
            return redirect(url_for("public.careers", _anchor="apply"))

        stored_name = secure_resume_filename(uploaded.filename)
        upload_path = current_app.config["UPLOAD_FOLDER"] / stored_name
        uploaded.save(upload_path)

        application = Application(
            full_name=sanitize_text(form.full_name.data, max_length=160),
            email=form.email.data.lower().strip(),
            phone=sanitize_text(form.phone.data, max_length=60),
            address=sanitize_text(form.address.data, max_length=240),
            position=sanitize_text(form.position.data, max_length=160),
            experience=sanitize_text(form.experience.data, max_length=80),
            skills=sanitize_text(form.skills.data, max_length=1200, preserve_newlines=True),
            portfolio_url=sanitize_text(form.portfolio_url.data, max_length=500),
            cover_letter=sanitize_text(form.cover_letter.data, max_length=3000, preserve_newlines=True),
            resume_filename=stored_name,
            original_resume_name=sanitize_text(uploaded.filename, max_length=255),
        )
        db.session.add(application)
        log_public_activity("create", "application", f"Submitted application for {application.position}.")
        db.session.commit()

        flash("Application received. Our hiring team will review it carefully.", "success")
        return redirect(url_for("public.careers", _anchor="jobs"))

    return render_template("careers.html", jobs=jobs, form=form, captcha_prompt=captcha_prompt)


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = prepare_inquiry_form()
    captcha_prompt = prepare_captcha(form, "contact-inquiry")
    if form.validate_on_submit():
        if not verify_form_captcha(form, "contact-inquiry"):
            return redirect(url_for("public.contact"))

        normalized_email = form.email.data.lower().strip()
        normalized_subject = sanitize_text(form.subject.data, max_length=180) or "General enquiry"
        normalized_service = sanitize_text(form.service.data, max_length=160) or "General"
        normalized_message = sanitize_text(form.message.data, max_length=2000, preserve_newlines=True)
        duplicate_window = max(1, (int(current_app.config.get("INQUIRY_DUPLICATE_WINDOW_SECONDS", 600)) + 59) // 60)
        if duplicate_inquiry_exists(
            email=normalized_email,
            subject=normalized_subject,
            service=normalized_service,
            message=normalized_message,
            window_minutes=duplicate_window,
        ):
            flash("We already received this enquiry recently. Please wait a moment before trying again.", "error")
            return redirect(url_for("public.contact"))

        inquiry = Inquiry(
            full_name=sanitize_text(form.full_name.data, max_length=160),
            email=normalized_email,
            subject=normalized_subject,
            phone=sanitize_text(form.phone.data, max_length=60),
            company=sanitize_text(form.company.data, max_length=160),
            country=sanitize_text(form.country.data, max_length=100),
            job_title=sanitize_text(form.job_title.data, max_length=120),
            service=normalized_service,
            contact_method=sanitize_text(form.contact_method.data, max_length=60),
            budget=sanitize_text(form.budget.data, max_length=80),
            message=normalized_message,
            ip_address=client_ip(),
        )
        db.session.add(inquiry)
        log_public_activity("create", "inquiry", f"Submitted inquiry for {inquiry.service}.")
        db.session.commit()
        flash("Your enquiry has been received. We will review it and respond using the contact details you shared.", "success")
        return redirect(url_for("public.contact"))

    settings = safe_active_settings_map()
    return render_template("contact.html", form=form, captcha_prompt=captcha_prompt, settings=settings)


@public_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    form = FeedbackForm()
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")
    if not form.validate_on_submit():
        errors = {field_name: field_errors for field_name, field_errors in form.errors.items()}
        message = "Please correct the highlighted feedback fields and try again."
        if wants_json:
            return jsonify({"ok": False, "message": message, "errors": errors}), 400
        flash(message, "error")
        return redirect(request.referrer or url_for("public.home"))

    normalized_email = form.email.data.lower().strip()
    normalized_message = sanitize_text(form.message.data, max_length=2000, preserve_newlines=True)
    duplicate_window = max(1, (int(current_app.config.get("FEEDBACK_DUPLICATE_WINDOW_SECONDS", 600)) + 59) // 60)
    if duplicate_feedback_exists(email=normalized_email, message=normalized_message, window_minutes=duplicate_window):
        message = "We already received this feedback recently. Please adjust the note if you need to add more context."
        if wants_json:
            return jsonify({"ok": False, "message": message, "errors": {}}), 400
        flash(message, "error")
        return redirect(request.referrer or url_for("public.home"))

    feedback = build_feedback_record(
        form,
        source_page=form.source_page.data or request.referrer or request.path,
        ip_address=client_ip(),
    )
    db.session.add(feedback)
    log_public_activity("create", "feedback", "Submitted website feedback.")
    db.session.commit()
    tone = "success"
    response_message = "Thanks for sharing your feedback. We will review it before publishing it on the site."

    response_payload = {
        "ok": True,
        "message": response_message,
        "tone": tone,
        "feedback": {
            "name": feedback.full_name,
            "rating": feedback.rating,
            "status": feedback.status,
        },
    }
    if wants_json:
        return jsonify(response_payload)

    flash(response_payload["message"], response_payload["tone"])
    return redirect(request.referrer or url_for("public.home"))


@public_bp.route("/newsletter", methods=["POST"])
def newsletter():
    form = NewsletterForm()
    if not form.validate_on_submit():
        flash("Enter a valid email address for the newsletter.", "error")
        return redirect(request.referrer or url_for("public.home"))

    email = form.email.data.lower().strip()
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    new_subscription = existing is None
    if existing:
        existing.is_active = True
    else:
        db.session.add(NewsletterSubscriber(email=email, source="Footer"))
        log_public_activity("create", "newsletter", f"Subscribed {email} to the newsletter.")
    db.session.commit()
    if new_subscription:
        flash("You are subscribed to AI SOLUTION insights.", "success")
    else:
        flash("You are already on the AI SOLUTION newsletter list.", "success")
    return redirect(request.referrer or url_for("public.home"))


@public_bp.route("/privacy")
def privacy():
    custom_policy = SiteSetting.query.filter_by(key="privacy_policy_body", active=True, archived=False).first()
    return render_template("privacy.html", custom_policy=custom_policy.value_text if custom_policy else "")


@public_bp.route("/terms")
def terms():
    return render_template("terms.html")


@public_bp.route("/robots.txt")
def robots_txt():
    sitemap_url = url_for("public.sitemap_xml", _external=True)
    admin_prefix = current_app.config.get("ADMIN_ROUTE_PREFIX", "/secure-admin").rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Disallow: {admin_prefix}/\n"
        "Disallow: /api/\n"
        "Disallow: /login\n"
        "Disallow: /workspace\n"
        "Disallow: /login/reset/\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return Response(content, mimetype="text/plain")


@public_bp.route("/sitemap.xml")
def sitemap_xml():
    urls: list[str] = []
    for endpoint, values in site_map_entries():
        if values:
            urls.append(url_for(endpoint, _external=True, **values))
        else:
            urls.append(url_for(endpoint, _external=True))

    items = []
    today = utcnow().date().isoformat()
    for url in urls:
        items.append(
            f"  <url><loc>{escape(url)}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )

    sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(items)
    sitemap += "\n</urlset>\n"
    return Response(sitemap, mimetype="application/xml")
