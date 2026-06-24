from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Response,
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from sqlalchemy import func, or_

from ..extensions import db
from ..forms import AdminLoginForm, StaffForm
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
    MediaAsset,
    NewsletterSubscriber,
    PublicUser,
    RSVP,
    Service,
    SiteSetting,
    TeamMember,
    Testimonial,
    User,
    WebsiteVisit,
    utcnow,
)
from ..utils.security import (
    allowed_media_file,
    build_numeric_captcha,
    client_ip,
    create_session_identifier,
    is_login_rate_limited,
    is_suspicious_login,
    parse_user_agent,
    sanitize_text,
    secure_media_filename,
    verify_numeric_captcha,
)
from ..utils.site import split_list_text


admin_bp = Blueprint("admin", __name__, template_folder="../../templates/admin")


CONTENT_RESOURCES = {
    "services": {
        "title": "Services",
        "model": Service,
        "search_fields": ["title", "category", "description"],
        "fields": [
            ("title", "Title", "text"),
            ("category", "Category", "text"),
            ("icon", "Lucide Icon", "text"),
            ("description", "Description", "textarea"),
            ("image_url", "Image URL", "text"),
            ("active", "Published", "checkbox"),
        ],
    },
    "industries": {
        "title": "Industries",
        "singular": "Industry",
        "model": Industry,
        "search_fields": ["name", "overview", "solution"],
        "fields": [
            ("name", "Name", "text"),
            ("slug", "Slug", "text"),
            ("image_url", "Image URL", "text"),
            ("overview", "Overview", "textarea"),
            ("problems", "Problems", "textarea"),
            ("solution", "Solution", "textarea"),
            ("benefits", "Benefits (one per line)", "list"),
            ("use_cases", "Use Cases (one per line)", "list"),
            ("active", "Published", "checkbox"),
        ],
    },
    "events": {
        "title": "Events",
        "singular": "Event",
        "model": Event,
        "search_fields": ["title", "location", "details"],
        "fields": [
            ("title", "Title", "text"),
            ("banner_image", "Banner Image URL", "text"),
            ("event_date", "Event Date", "date"),
            ("event_time", "Event Time", "text"),
            ("location", "Location", "text"),
            ("details", "Event Details", "textarea"),
            ("active", "Published", "checkbox"),
        ],
    },
    "blogs": {
        "title": "Blogs",
        "model": BlogPost,
        "search_fields": ["title", "category", "author", "description", "content"],
        "fields": [
            ("title", "Title", "text"),
            ("slug", "Slug", "text"),
            ("image_url", "Featured Image URL", "text"),
            ("description", "Summary", "textarea"),
            ("content", "Article Content", "textarea"),
            ("author", "Author", "text"),
            ("category", "Category", "text"),
            ("publish_date", "Publish Date", "date"),
            ("featured", "Featured Post", "checkbox"),
            ("meta_title", "Meta Title", "text"),
            ("meta_description", "Meta Description", "textarea"),
            ("active", "Published", "checkbox"),
        ],
    },
    "testimonials": {
        "title": "Testimonials",
        "model": Testimonial,
        "search_fields": ["customer_name", "company_name", "role", "feedback"],
        "fields": [
            ("customer_name", "Customer Name", "text"),
            ("company_name", "Company", "text"),
            ("role", "Role", "text"),
            ("rating", "Rating", "number"),
            ("profile_image", "Profile Image URL", "text"),
            ("feedback", "Feedback", "textarea"),
            ("active", "Published", "checkbox"),
        ],
    },
    "case-studies": {
        "title": "Case Studies",
        "model": CaseStudy,
        "search_fields": ["title", "client_industry", "impact", "technologies"],
        "fields": [
            ("title", "Title", "text"),
            ("client_industry", "Client Industry", "text"),
            ("technologies", "Technologies", "text"),
            ("impact", "Business Impact", "text"),
            ("before_result", "Before Result", "text"),
            ("after_result", "After Result", "text"),
            ("image_url", "Image URL", "text"),
            ("active", "Published", "checkbox"),
        ],
    },
    "jobs": {
        "title": "Jobs",
        "model": Job,
        "search_fields": ["title", "department", "location", "description"],
        "fields": [
            ("title", "Title", "text"),
            ("department", "Department", "text"),
            ("location", "Location", "text"),
            ("employment_type", "Type", "text"),
            ("description", "Description", "textarea"),
            ("requirements", "Requirements", "textarea"),
            ("active", "Published", "checkbox"),
        ],
    },
    "faq": {
        "title": "FAQ",
        "model": FaqItem,
        "search_fields": ["question", "answer", "category"],
        "fields": [
            ("question", "Question", "text"),
            ("answer", "Answer", "textarea"),
            ("category", "Category", "text"),
            ("sort_order", "Sort Order", "number"),
            ("active", "Published", "checkbox"),
        ],
    },
    "team": {
        "title": "Team Members",
        "model": TeamMember,
        "search_fields": ["name", "role", "bio"],
        "fields": [
            ("name", "Name", "text"),
            ("role", "Role", "text"),
            ("bio", "Biography", "textarea"),
            ("image_url", "Image URL", "text"),
            ("linkedin_url", "LinkedIn URL", "text"),
            ("sort_order", "Sort Order", "number"),
            ("active", "Published", "checkbox"),
        ],
    },
    "media": {
        "title": "Media Library",
        "model": MediaAsset,
        "search_fields": ["title", "category", "alt_text", "source"],
        "fields": [
            ("title", "Title", "text"),
            ("file_url", "File URL", "text"),
            ("alt_text", "Alt Text", "text"),
            ("category", "Category", "text"),
            ("source", "Source", "text"),
            ("active", "Published", "checkbox"),
        ],
    },
    "site-settings": {
        "title": "Site Settings",
        "model": SiteSetting,
        "search_fields": ["key", "label", "category", "value_text"],
        "fields": [
            ("label", "Label", "text"),
            ("key", "Key", "text"),
            ("category", "Category", "text"),
            ("value_type", "Value Type", "text"),
            ("value_text", "Value", "textarea"),
            ("description", "Description", "textarea"),
            ("active", "Published", "checkbox"),
        ],
    },
}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("staff_user_id")
        if not user_id:
            return redirect(url_for("admin.login"))
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for("admin.login"))
        g.staff_user = user
        return view(*args, **kwargs)

    return wrapped


def current_staff_user() -> User | None:
    user_id = session.get("staff_user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def role_required(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_staff_user()
            if not user or (user.role not in roles and user.role != "Super Admin"):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


RESOURCE_ROLE_ACCESS = {
    "services": {"Super Admin", "Admin", "Content Manager"},
    "industries": {"Super Admin", "Admin", "Content Manager"},
    "events": {"Super Admin", "Admin", "Event Manager"},
    "blogs": {"Super Admin", "Admin", "Content Manager"},
    "testimonials": {"Super Admin", "Admin", "Content Manager"},
    "case-studies": {"Super Admin", "Admin", "Content Manager"},
    "jobs": {"Super Admin", "Admin", "HR Manager"},
    "faq": {"Super Admin", "Admin", "Content Manager"},
    "team": {"Super Admin", "Admin", "Content Manager"},
    "media": {"Super Admin", "Admin", "Content Manager"},
    "site-settings": {"Super Admin", "Admin", "Content Manager"},
    "feedback": {"Super Admin", "Admin", "Content Manager"},
}

ALLOWED_STAFF_ROLES = {"Super Admin", "Admin", "HR Manager", "Event Manager", "Content Manager"}


def require_resource_access(resource: str) -> None:
    allowed_roles = RESOURCE_ROLE_ACCESS.get(resource, {"Super Admin", "Admin"})
    user = current_staff_user()
    if not user or (user.role not in allowed_roles and user.role != "Super Admin"):
        abort(403)


def log_admin_activity(action: str, resource_type: str, description: str, *, resource_id: str | None = None, details=None) -> None:
    staff_user = current_staff_user()
    actor_name = staff_user.name if staff_user else "System"
    db.session.add(
        ActivityLog(
            actor_type="admin",
            actor_name=actor_name,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            description=description,
            ip_address=client_ip(),
            user_agent=(request.user_agent.string or "")[:300],
            staff_user_id=staff_user.id if staff_user else None,
            details=details or {},
        )
    )


def record_auth_event(
    *,
    user_type: str,
    email: str,
    success: bool,
    session_identifier: str,
    staff_user: User | None = None,
    public_user: PublicUser | None = None,
    suspicious: bool = False,
    failure_reason: str | None = None,
) -> AuthSessionLog:
    agent = parse_user_agent(request.user_agent.string or "")
    event = AuthSessionLog(
        user_type=user_type,
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
        staff_user_id=staff_user.id if staff_user else None,
        public_user_id=public_user.id if public_user else None,
    )
    db.session.add(event)
    return event


def complete_admin_login(
    *,
    user: User,
    email: str,
    session_identifier: str,
    remember: bool,
    suspicious: bool,
) -> None:
    session.clear()
    session["staff_user_id"] = user.id
    session["staff_role"] = user.role
    session["staff_session_identifier"] = session_identifier
    session.permanent = bool(remember)
    user.last_login_at = utcnow()
    user.last_login_ip = client_ip()
    user.failed_login_count = 0
    auth_event = record_auth_event(
        user_type="admin",
        email=email,
        success=True,
        session_identifier=session_identifier,
        staff_user=user,
        suspicious=suspicious,
    )
    db.session.flush()
    session["staff_session_log_id"] = auth_event.id
    log_admin_activity(
        "login",
        "auth",
        "Staff user signed in to the admin dashboard.",
        resource_id=str(user.id),
        details={"suspicious": suspicious},
    )


def list_query(model, search_fields: list[str]):
    query = model.query
    search = sanitize_text(request.args.get("q"), max_length=120)
    state = sanitize_text(request.args.get("state"), max_length=20)
    status_filter = sanitize_text(request.args.get("status"), max_length=50)
    sort = sanitize_text(request.args.get("sort"), max_length=50) or "created_at"
    direction = sanitize_text(request.args.get("direction"), max_length=4) or "desc"
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 5), 50)

    if search and search_fields:
        filters = [getattr(model, column).cast(db.String).ilike(f"%{search}%") for column in search_fields if hasattr(model, column)]
        if filters:
            query = query.filter(or_(*filters))

    if hasattr(model, "archived") and state == "archived":
        query = query.filter(model.archived.is_(True))
    elif hasattr(model, "archived") and state == "published":
        query = query.filter(model.active.is_(True), model.archived.is_(False))
    elif hasattr(model, "archived") and state == "draft":
        query = query.filter(model.active.is_(False), model.archived.is_(False))

    if status_filter and hasattr(model, "status"):
        query = query.filter(model.status == status_filter)

    sort_column = getattr(model, sort, None)
    if sort_column is None:
        sort_column = getattr(model, "created_at", getattr(model, "id"))
    order_by = sort_column.asc() if direction == "asc" else sort_column.desc()
    query = query.order_by(order_by)

    total = query.count()
    records = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max((total + per_page - 1) // per_page, 1)
    return {
        "records": records,
        "search": search,
        "state": state or "all",
        "status_filter": status_filter,
        "sort": sort,
        "direction": direction,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "total": total,
    }


IMAGE_FIELD_NAMES = {"image_url", "profile_image", "banner_image", "file_url"}


def is_uploadable_image_field(resource: str, record, field_name: str) -> bool:
    if field_name in IMAGE_FIELD_NAMES:
        return True
    if resource == "site-settings" and field_name == "value_text":
        key = (getattr(record, "key", "") or "").lower()
        return "image" in key or "banner" in key or "avatar" in key
    return False


def remove_local_media_file(file_url: str | None) -> None:
    file_url = (file_url or "").strip()
    media_prefix = url_for("public.uploaded_media", filename="")
    if not file_url.startswith(media_prefix):
        return
    filename = file_url.removeprefix(media_prefix).lstrip("/")
    if not filename:
        return
    target = current_app.config["MEDIA_UPLOAD_FOLDER"] / filename
    if target.exists():
        target.unlink(missing_ok=True)


def store_media_upload(uploaded) -> str | None:
    if not uploaded or not uploaded.filename:
        return None
    if not allowed_media_file(uploaded.filename):
        return None
    stored_name = secure_media_filename(uploaded.filename)
    uploaded.save(current_app.config["MEDIA_UPLOAD_FOLDER"] / stored_name)
    return url_for("public.uploaded_media", filename=stored_name)


@admin_bp.route("/")
def root():
    return redirect(url_for("admin.dashboard") if session.get("staff_user_id") else url_for("admin.login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    form = AdminLoginForm()
    captcha = build_numeric_captcha("admin-login")
    form.captcha_scope.data = "admin-login"

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        session_identifier = create_session_identifier()
        agent = parse_user_agent(request.user_agent.string or "")
        suspicious = is_suspicious_login(email, "admin", client_ip(), agent["browser"], agent["operating_system"])
        if is_login_rate_limited(email, "admin"):
            record_auth_event(
                user_type="admin",
                email=email,
                success=False,
                session_identifier=session_identifier,
                failure_reason="Rate limited",
                suspicious=suspicious,
            )
            db.session.commit()
            flash("Too many failed attempts. Please wait before trying again.", "error")
            return redirect(url_for("admin.login"))

        verified, message = verify_numeric_captcha(form.captcha_scope.data or "admin-login", form.captcha_answer.data)
        if not verified:
            record_auth_event(
                user_type="admin",
                email=email,
                success=False,
                session_identifier=session_identifier,
                failure_reason="CAPTCHA validation failed",
                suspicious=suspicious,
            )
            db.session.commit()
            flash(message, "error")
            return redirect(url_for("admin.login"))

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user or not user.is_active or not user.check_password(form.password.data):
            if user:
                user.failed_login_count += 1
            record_auth_event(
                user_type="admin",
                email=email,
                success=False,
                session_identifier=session_identifier,
                failure_reason="Invalid credentials",
                suspicious=suspicious,
            )
            db.session.commit()
            flash("Invalid credentials or inactive staff account.", "error")
            return redirect(url_for("admin.login"))
        complete_admin_login(
            user=user,
            email=email,
            session_identifier=session_identifier,
            remember=bool(form.remember.data),
            suspicious=suspicious,
        )
        db.session.commit()
        if suspicious:
            flash("Suspicious login pattern detected. The event has been logged for review.", "error")
        flash("Welcome back to the AI SOLUTION control center.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/login.html",
        form=form,
        captcha_prompt=captcha["prompt"],
    )


@admin_bp.route("/logout")
@admin_required
def logout():
    session_log_id = session.get("staff_session_log_id")
    if session_log_id:
        auth_event = db.session.get(AuthSessionLog, session_log_id)
        if auth_event and not auth_event.logged_out_at:
            auth_event.logged_out_at = utcnow()
    log_admin_activity("logout", "auth", "Staff user signed out of the admin dashboard.")
    db.session.commit()
    session.pop("staff_user_id", None)
    session.pop("staff_role", None)
    session.pop("staff_session_identifier", None)
    session.pop("staff_session_log_id", None)
    flash("You have been signed out.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    counts = {
        "Inquiries": Inquiry.query.count(),
        "Applications": Application.query.count(),
        "RSVPs": RSVP.query.count(),
        "Client Accounts": PublicUser.query.count(),
        "Feedback": Feedback.query.count(),
        "Pending Feedback": Feedback.query.filter_by(status="Pending").count(),
        "Chatbot Logs": ChatbotLog.query.count(),
        "Site Visits": WebsiteVisit.query.count(),
        "Published Blogs": BlogPost.query.filter_by(active=True, archived=False).count(),
        "Failed Logins (24h)": AuthSessionLog.query.filter_by(success=False).filter(AuthSessionLog.logged_in_at >= utcnow() - timedelta(hours=24)).count(),
    }
    chart_data = {
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "inquiries": monthly_counts(Inquiry),
        "applications": monthly_counts(Application),
        "rsvps": monthly_counts(RSVP),
        "chatbot": monthly_counts(ChatbotLog),
        "countries": country_counts(),
        "services": service_interest_counts(),
        "logins": monthly_counts(AuthSessionLog, success_only=True),
    }
    notifications = build_notifications()
    quick_actions = [
        {"label": "Create Blog", "url": url_for("admin.manage_content", resource="blogs")},
        {"label": "Review Inquiries", "url": url_for("admin.inquiries")},
        {"label": "Review Feedback", "url": url_for("admin.feedback")},
        {"label": "Manage FAQ", "url": url_for("admin.manage_content", resource="faq")},
        {"label": "Site Settings", "url": url_for("admin.manage_content", resource="site-settings")},
    ]
    latest_inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).limit(5).all()
    latest_apps = Application.query.order_by(Application.created_at.desc()).limit(5).all()
    latest_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(5).all()
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(8).all()
    recent_auth = AuthSessionLog.query.order_by(AuthSessionLog.logged_in_at.desc()).limit(8).all()
    return render_template(
        "admin/dashboard.html",
        counts=counts,
        chart_data=chart_data,
        notifications=notifications,
        quick_actions=quick_actions,
        latest_inquiries=latest_inquiries,
        latest_apps=latest_apps,
        latest_feedback=latest_feedback,
        recent_activity=recent_activity,
        recent_auth=recent_auth,
    )


@admin_bp.route("/inquiries")
@admin_required
@role_required("Super Admin", "Admin", "Content Manager")
def inquiries():
    listing = list_query(Inquiry, ["full_name", "email", "subject", "company", "country", "service", "status", "created_at"])
    return render_template(
        "admin/table.html",
        title="Inquiries",
        records=listing["records"],
        columns=["full_name", "email", "subject", "company", "country", "service", "status", "created_at"],
        statuses=["New", "Contacted", "Qualified", "Closed"],
        download=False,
        search=listing["search"],
        state=listing["state"],
        status_filter=listing["status_filter"],
        sort=listing["sort"],
        direction=listing["direction"],
        page=listing["page"],
        pages=listing["pages"],
        total=listing["total"],
        table_actions="inquiries",
        export_endpoint="admin.export_inquiries",
        allow_delete=True,
    )


@admin_bp.route("/inquiries/export.csv")
@admin_required
def export_inquiries() -> Response:
    query = Inquiry.query.order_by(Inquiry.created_at.desc())
    search = sanitize_text(request.args.get("q"), max_length=120)
    status_filter = sanitize_text(request.args.get("status"), max_length=50)
    if search:
        query = query.filter(
            or_(
                Inquiry.full_name.cast(db.String).ilike(f"%{search}%"),
                Inquiry.email.cast(db.String).ilike(f"%{search}%"),
                Inquiry.subject.cast(db.String).ilike(f"%{search}%"),
                Inquiry.company.cast(db.String).ilike(f"%{search}%"),
                Inquiry.country.cast(db.String).ilike(f"%{search}%"),
                Inquiry.service.cast(db.String).ilike(f"%{search}%"),
                Inquiry.status.cast(db.String).ilike(f"%{search}%"),
            )
        )
    if status_filter:
        query = query.filter(Inquiry.status == status_filter)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Full Name", "Email", "Subject", "Phone", "Company", "Country", "Job Title", "Service", "Contact Method", "Budget", "Message", "Status", "Created At"])
    for inquiry in query.all():
        writer.writerow(
            [
                inquiry.full_name,
                inquiry.email,
                inquiry.subject,
                inquiry.phone,
                inquiry.company,
                inquiry.country,
                inquiry.job_title,
                inquiry.service,
                inquiry.contact_method,
                inquiry.budget,
                inquiry.message,
                inquiry.status,
                inquiry.created_at.strftime("%Y-%m-%d %H:%M:%S") if inquiry.created_at else "",
            ]
        )
    filename = f"ai-solution-inquiries-{datetime.now():%Y%m%d-%H%M%S}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_bp.route("/applications")
@admin_required
@role_required("Super Admin", "Admin", "HR Manager")
def applications():
    return data_table(
        "Applications",
        Application,
        ["full_name", "email", "position", "experience", "status", "created_at"],
        ["Received", "Screening", "Interview", "Offer", "Rejected"],
        download=True,
    )


@admin_bp.route("/applications/<int:application_id>/resume")
@admin_required
def download_resume(application_id: int):
    application = db.session.get(Application, application_id) or abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        application.resume_filename,
        as_attachment=True,
        download_name=application.original_resume_name,
    )


@admin_bp.route("/rsvps")
@admin_required
@role_required("Super Admin", "Admin", "Event Manager")
def rsvps():
    return data_table(
        "RSVPs",
        RSVP,
        ["full_name", "email", "company", "job_title", "preferred_session", "attendees", "status", "created_at"],
        ["Confirmed", "Waitlisted", "Cancelled", "Attended"],
    )


@admin_bp.route("/chatbot-logs")
@admin_required
@role_required("Super Admin", "Admin")
def chatbot_logs():
    return data_table(
        "Chatbot Logs",
        ChatbotLog,
        ["session_id", "intent", "user_message", "bot_response", "created_at"],
        None,
    )


@admin_bp.route("/newsletter")
@admin_required
@role_required("Super Admin", "Admin", "Content Manager")
def newsletter():
    return data_table(
        "Newsletter Subscribers",
        NewsletterSubscriber,
        ["email", "source", "is_active", "created_at"],
        None,
    )


@admin_bp.route("/records/<resource>/<int:record_id>/delete", methods=["POST"])
@admin_required
def delete_record(resource: str, record_id: int):
    require_resource_access(resource)
    model_map = {
        "inquiries": Inquiry,
        "applications": Application,
        "rsvps": RSVP,
        "newsletter": NewsletterSubscriber,
        "chatbot-logs": ChatbotLog,
        "feedback": Feedback,
    }
    model = model_map.get(resource)
    if not model:
        abort(404)

    record = db.session.get(model, record_id) or abort(404)
    if isinstance(record, Application) and record.resume_filename:
        resume_path = current_app.config["UPLOAD_FOLDER"] / record.resume_filename
        if resume_path.exists():
            resume_path.unlink(missing_ok=True)
    log_admin_activity("delete", resource, f"Deleted {resource.replace('-', ' ')} record.", resource_id=str(record_id))
    db.session.delete(record)
    db.session.commit()
    flash("Record deleted.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/clients")
@admin_required
@role_required("Super Admin", "Admin")
def client_users():
    columns = ["full_name", "company", "email", "is_active", "last_login_at", "accepted_privacy"]
    listing = list_query(PublicUser, columns)
    return render_template(
        "admin/table.html",
        title="Client Users",
        records=listing["records"],
        columns=columns,
        statuses=None,
        download=False,
        search=listing["search"],
        state=listing["state"],
        status_filter=listing["status_filter"],
        sort=listing["sort"],
        direction=listing["direction"],
        page=listing["page"],
        pages=listing["pages"],
        total=listing["total"],
        table_actions="clients",
        export_endpoint=None,
        allow_delete=False,
    )


@admin_bp.route("/clients/<int:user_id>", methods=["POST"])
@admin_required
@role_required("Super Admin", "Admin")
def update_client_user(user_id: int):
    user = db.session.get(PublicUser, user_id) or abort(404)
    action = request.form.get("action")
    if action == "archive":
        user.is_active = False
        log_admin_activity("archive", "client-user", f"Archived client account for {user.email}.", resource_id=str(user.id))
    elif action == "restore":
        user.is_active = True
        log_admin_activity("restore", "client-user", f"Restored client account for {user.email}.", resource_id=str(user.id))
    elif action == "delete":
        log_admin_activity("delete", "client-user", f"Deleted client account for {user.email}.", resource_id=str(user.id))
        db.session.delete(user)
        db.session.commit()
        flash("Client account deleted.", "success")
        return redirect(url_for("admin.client_users"))
    db.session.commit()
    flash("Client account updated.", "success")
    return redirect(url_for("admin.client_users"))


@admin_bp.route("/auth-logs")
@admin_required
@role_required("Super Admin", "Admin")
def auth_logs():
    columns = [
        "user_type",
        "email",
        "success",
        "suspicious",
        "ip_address",
        "browser",
        "device",
        "operating_system",
        "failure_reason",
        "logged_in_at",
        "logged_out_at",
    ]
    listing = list_query(AuthSessionLog, columns)
    return render_template(
        "admin/table.html",
        title="Authentication Logs",
        records=listing["records"],
        columns=columns,
        statuses=None,
        download=False,
        search=listing["search"],
        state=listing["state"],
        status_filter=listing["status_filter"],
        sort=listing["sort"],
        direction=listing["direction"],
        page=listing["page"],
        pages=listing["pages"],
        total=listing["total"],
        table_actions="auth",
        export_endpoint=None,
        allow_delete=False,
    )


@admin_bp.route("/activity-logs")
@admin_required
@role_required("Super Admin", "Admin")
def activity_logs():
    columns = ["actor_name", "action", "resource_type", "description", "ip_address", "created_at"]
    listing = list_query(ActivityLog, columns)
    return render_template(
        "admin/table.html",
        title="Activity Logs",
        records=listing["records"],
        columns=columns,
        statuses=None,
        download=False,
        search=listing["search"],
        state=listing["state"],
        status_filter=listing["status_filter"],
        sort=listing["sort"],
        direction=listing["direction"],
        page=listing["page"],
        pages=listing["pages"],
        total=listing["total"],
        table_actions="activity",
        export_endpoint=None,
        allow_delete=False,
    )


def data_table(title, model, columns, statuses=None, download=False):
    listing = list_query(model, columns)
    return render_template(
        "admin/table.html",
        title=title,
        records=listing["records"],
        columns=columns,
        statuses=statuses,
        download=download,
        search=listing["search"],
        state=listing["state"],
        status_filter=listing["status_filter"],
        sort=listing["sort"],
        direction=listing["direction"],
        page=listing["page"],
        pages=listing["pages"],
        total=listing["total"],
        table_actions=request.endpoint.split(".")[-1],
        export_endpoint=None,
        allow_delete=False,
    )


@admin_bp.route("/status/<resource>/<int:record_id>", methods=["POST"])
@admin_required
def update_status(resource: str, record_id: int):
    require_resource_access(resource)
    model_map = {"inquiries": Inquiry, "applications": Application, "rsvps": RSVP, "feedback": Feedback}
    model = model_map.get(resource)
    if not model:
        abort(404)
    record = db.session.get(model, record_id) or abort(404)
    status = sanitize_text(request.form.get("status"), max_length=50) or "Pending"
    record.status = status
    if resource == "feedback":
        if status == "Approved" and hasattr(record, "publish"):
            record.publish()
        else:
            record.active = False
            record.archived = False
    log_admin_activity("status-update", resource, f"Updated {resource} status to {record.status}.", resource_id=str(record_id))
    db.session.commit()
    flash("Status updated.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/feedback")
@admin_required
@role_required("Super Admin", "Admin", "Content Manager")
def feedback():
    columns = ["full_name", "email", "rating", "message", "status", "source_page", "created_at"]
    listing = list_query(Feedback, columns)
    return render_template(
        "admin/table.html",
        title="Feedback",
        records=listing["records"],
        columns=columns,
        statuses=["Pending", "Approved", "Rejected"],
        download=False,
        search=listing["search"],
        state=listing["state"],
        status_filter=listing["status_filter"],
        sort=listing["sort"],
        direction=listing["direction"],
        page=listing["page"],
        pages=listing["pages"],
        total=listing["total"],
        table_actions="feedback",
        export_endpoint=None,
        allow_delete=True,
    )


@admin_bp.route("/manage/<resource>", methods=["GET", "POST"])
@admin_required
def manage_content(resource: str):
    config = CONTENT_RESOURCES.get(resource)
    if not config:
        abort(404)
    require_resource_access(resource)
    model = config["model"]

    if request.method == "POST":
        action = request.form.get("action", "save")
        record_id = request.form.get("record_id", type=int)
        record = db.session.get(model, record_id) if record_id else model()
        if action == "delete":
            record = db.session.get(model, record_id) or abort(404)
            if resource == "media":
                remove_local_media_file(record.file_url)
            else:
                for field_name, _label, _field_type in config["fields"]:
                    if is_uploadable_image_field(resource, record, field_name):
                        remove_local_media_file(getattr(record, field_name, ""))
            log_admin_activity("delete", resource, f"Deleted {config['title']} record.", resource_id=str(record.id))
            db.session.delete(record)
            db.session.commit()
            flash(f"{config['title']} record deleted.", "success")
            return redirect(url_for("admin.manage_content", resource=resource))

        apply_content_fields(record, config["fields"])
        if resource == "media":
            uploaded = request.files.get("upload_file")
            if uploaded and uploaded.filename:
                file_url = store_media_upload(uploaded)
                if not file_url:
                    flash("Upload PNG, JPG, JPEG, WEBP, or GIF media files only.", "error")
                    return redirect(url_for("admin.manage_content", resource=resource))
                remove_local_media_file(record.file_url)
                record.file_url = file_url
                if not sanitize_text(request.form.get("alt_text"), max_length=255):
                    record.alt_text = Path(uploaded.filename).stem.replace("-", " ").replace("_", " ").title()
            if not getattr(record, "file_url", ""):
                flash("Provide a media URL or upload an image file.", "error")
                return redirect(url_for("admin.manage_content", resource=resource))
        else:
            for field_name, _label, _field_type in config["fields"]:
                if not is_uploadable_image_field(resource, record, field_name):
                    continue
                uploaded = request.files.get(f"upload_{field_name}")
                if not uploaded or not uploaded.filename:
                    continue
                file_url = store_media_upload(uploaded)
                if not file_url:
                    flash("Upload PNG, JPG, JPEG, WEBP, or GIF media files only.", "error")
                    return redirect(url_for("admin.manage_content", resource=resource))
                remove_local_media_file(getattr(record, field_name, ""))
                setattr(record, field_name, file_url)
        if hasattr(record, "slug") and not getattr(record, "slug", "") and getattr(record, "title", ""):
            from ..data import slugify

            record.slug = slugify(record.title)
        if action == "archive" and hasattr(record, "archive"):
            record.archive()
        elif action == "restore" and hasattr(record, "restore"):
            record.restore()
        elif action == "publish" and hasattr(record, "publish"):
            record.publish()
        db.session.add(record)
        log_admin_activity(action, resource, f"{config['title']} record {action}d.", resource_id=str(record.id or "new"))
        db.session.commit()
        flash(f"{config['title']} record saved.", "success")
        return redirect(url_for("admin.manage_content", resource=resource))

    listing = list_query(model, config["search_fields"])
    return render_template("admin/content.html", resource=resource, config=config, **listing)


def apply_content_fields(record, fields) -> None:
    for name, _label, field_type in fields:
        if field_type == "checkbox":
            setattr(record, name, request.form.get(name) == "on")
        elif field_type == "date":
            raw = request.form.get(name)
            setattr(record, name, datetime.strptime(raw, "%Y-%m-%d").date() if raw else date.today())
        elif field_type == "number":
            setattr(record, name, int(request.form.get(name, 0) or 0))
        elif field_type == "list":
            setattr(record, name, split_list_text(request.form.get(name)))
        elif field_type == "textarea":
            setattr(record, name, sanitize_text(request.form.get(name), max_length=8000, preserve_newlines=True))
        else:
            setattr(record, name, sanitize_text(request.form.get(name), max_length=500))


@admin_bp.route("/staff", methods=["GET", "POST"])
@admin_required
@role_required("Super Admin")
def staff():
    form = StaffForm()
    if form.validate_on_submit():
        existing = User.query.filter(func.lower(User.email) == form.email.data.lower().strip()).first()
        if existing:
            flash("A staff account with that email already exists.", "error")
            return redirect(url_for("admin.staff"))
        if not form.password.data:
            flash("Password is required for new staff accounts.", "error")
            return redirect(url_for("admin.staff"))
        user = User(
            name=sanitize_text(form.name.data, max_length=120),
            email=form.email.data.lower().strip(),
            role=form.role.data,
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        log_admin_activity("create", "staff", f"Created staff account for {user.email}.", resource_id=str(user.id or "new"))
        db.session.commit()
        flash("Staff account created.", "success")
        return redirect(url_for("admin.staff"))

    staff_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/staff.html", form=form, staff_users=staff_users)


@admin_bp.route("/staff/<int:user_id>", methods=["POST"])
@admin_required
@role_required("Super Admin")
def update_staff(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    action = request.form.get("action")
    if action == "delete":
        if user.id == session.get("staff_user_id"):
            flash("You cannot delete the account you are currently using.", "error")
        else:
            log_admin_activity("delete", "staff", f"Deleted staff account for {user.email}.", resource_id=str(user.id))
            db.session.delete(user)
            db.session.commit()
            flash("Staff account deleted.", "success")
        return redirect(url_for("admin.staff"))
    if action == "activate":
        user.is_active = True
    elif action == "deactivate":
        user.is_active = False

    user.name = sanitize_text(request.form.get("name"), max_length=120)
    user.role = sanitize_text(request.form.get("role"), max_length=50)
    if action not in {"activate", "deactivate"}:
        user.is_active = request.form.get("is_active") == "on"
    password = request.form.get("password", "")
    if password:
        user.set_password(password)
    role = sanitize_text(request.form.get("role"), max_length=50)
    if role not in ALLOWED_STAFF_ROLES:
        flash("Choose a valid staff role.", "error")
        return redirect(url_for("admin.staff"))
    user.role = role
    activity_action = action if action in {"activate", "deactivate"} else "update"
    log_admin_activity(activity_action, "staff", f"Updated staff account for {user.email}.", resource_id=str(user.id))
    db.session.commit()
    flash("Staff account updated.", "success")
    return redirect(url_for("admin.staff"))


def monthly_counts(model, *, success_only: bool = False) -> list[int]:
    year = datetime.now().year
    counts = [0] * 12
    query = db.session.query(model.created_at if hasattr(model, "created_at") else model.logged_in_at)
    if model is AuthSessionLog:
        query = db.session.query(AuthSessionLog.logged_in_at)
        if success_only:
            query = query.filter(AuthSessionLog.success.is_(True))
    for (created_at,) in query.all():
        if created_at and created_at.year == year:
            counts[created_at.month - 1] += 1
    return counts


def country_counts() -> dict:
    rows = (
        db.session.query(Inquiry.country, func.count(Inquiry.id))
        .filter(Inquiry.country.isnot(None))
        .group_by(Inquiry.country)
        .order_by(func.count(Inquiry.id).desc())
        .limit(8)
        .all()
    )
    labels = [row[0] or "Unknown" for row in rows] or ["United Kingdom", "Nepal", "United States", "Germany"]
    values = [row[1] for row in rows] or [32, 18, 15, 9]
    return {"labels": labels, "values": values}


def service_interest_counts() -> dict:
    rows = (
        db.session.query(Inquiry.service, func.count(Inquiry.id))
        .filter(Inquiry.service.isnot(None))
        .group_by(Inquiry.service)
        .order_by(func.count(Inquiry.id).desc())
        .limit(8)
        .all()
    )
    labels = [row[0] or "General" for row in rows] or [
        "AI Automation",
        "AI Analytics",
        "AI Cybersecurity",
        "Virtual Assistant Systems",
    ]
    values = [row[1] for row in rows] or [24, 19, 13, 11]
    return {"labels": labels, "values": values}


def build_notifications() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    pending_inquiries = Inquiry.query.filter(Inquiry.status.in_(["New", "Qualified"])).count()
    pending_feedback = Feedback.query.filter_by(status="Pending").count()
    suspicious_logins = AuthSessionLog.query.filter_by(suspicious=True).order_by(AuthSessionLog.logged_in_at.desc()).limit(1).first()
    archived_content = BlogPost.query.filter_by(archived=True).count() + Service.query.filter_by(archived=True).count()

    if pending_inquiries:
        items.append({"title": "Pending inquiries", "body": f"{pending_inquiries} inquiries still need active follow-up."})
    if pending_feedback:
        items.append({"title": "Pending feedback", "body": f"{pending_feedback} feedback items are waiting for review."})
    if suspicious_logins:
        items.append({"title": "Security review", "body": f"Suspicious login recorded for {suspicious_logins.email}."})
    if archived_content:
        items.append({"title": "Archived content", "body": f"{archived_content} content records are archived and available for restore."})
    if not items:
        items.append({"title": "Operations healthy", "body": "No urgent admin alerts are currently open."})
    return items
