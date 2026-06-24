from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class PublishMixin:
    active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    published_at = db.Column(db.DateTime(timezone=True))

    def publish(self) -> None:
        self.active = True
        self.archived = False
        if not self.published_at:
            self.published_at = utcnow()

    def archive(self) -> None:
        self.active = False
        self.archived = True

    def restore(self) -> None:
        self.active = True
        self.archived = False


class PasswordMixin:
    password_hash = db.Column(db.String(255), nullable=False)
    password_changed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class User(TimestampMixin, PasswordMixin, db.Model):
    __tablename__ = "staff_users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    role = db.Column(db.String(50), nullable=False, default="Support Staff")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    last_login_ip = db.Column(db.String(80))
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)


class PublicUser(TimestampMixin, PasswordMixin, db.Model):
    __tablename__ = "public_users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    company = db.Column(db.String(160))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    accepted_privacy = db.Column(db.Boolean, default=False, nullable=False)
    accepted_privacy_at = db.Column(db.DateTime(timezone=True))
    last_login_at = db.Column(db.DateTime(timezone=True))
    last_login_ip = db.Column(db.String(80))
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)


class Inquiry(TimestampMixin, db.Model):
    __tablename__ = "inquiries"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    subject = db.Column(db.String(180), default="General Inquiry", nullable=False)
    phone = db.Column(db.String(60))
    company = db.Column(db.String(160))
    country = db.Column(db.String(100), index=True)
    job_title = db.Column(db.String(120))
    service = db.Column(db.String(160), index=True)
    contact_method = db.Column(db.String(60))
    budget = db.Column(db.String(80))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default="New", nullable=False, index=True)
    ip_address = db.Column(db.String(80))


class NewsletterSubscriber(TimestampMixin, db.Model):
    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    source = db.Column(db.String(80), default="Website")
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Service(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    icon = db.Column(db.String(60), nullable=False, default="cpu")
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))


class Industry(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "industries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(140), nullable=False, unique=True, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    overview = db.Column(db.Text, nullable=False)
    problems = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    benefits = db.Column(db.JSON, nullable=False, default=list)
    use_cases = db.Column(db.JSON, nullable=False, default=list)


class Event(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    banner_image = db.Column(db.String(500), nullable=False)
    event_date = db.Column(db.Date, nullable=False, index=True)
    event_time = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(180), nullable=False)
    details = db.Column(db.Text, nullable=False)
    rsvps = db.relationship("RSVP", backref="event", lazy=True)


class RSVP(TimestampMixin, db.Model):
    __tablename__ = "rsvps"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(60))
    company = db.Column(db.String(160))
    job_title = db.Column(db.String(120))
    attendees = db.Column(db.Integer, default=1, nullable=False)
    preferred_session = db.Column(db.String(120))
    special_requirements = db.Column(db.Text)
    message = db.Column(db.Text)
    status = db.Column(db.String(40), default="Confirmed", nullable=False, index=True)


class BlogPost(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(240), unique=True, nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    publish_date = db.Column(db.Date, nullable=False, index=True)
    featured = db.Column(db.Boolean, default=False, nullable=False)
    meta_title = db.Column(db.String(255))
    meta_description = db.Column(db.String(320))


class Testimonial(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(140), nullable=False)
    company_name = db.Column(db.String(180), nullable=False)
    role = db.Column(db.String(140), nullable=False)
    rating = db.Column(db.Integer, default=5, nullable=False)
    profile_image = db.Column(db.String(500), nullable=False)
    feedback = db.Column(db.Text, nullable=False)


class Feedback(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "feedback_entries"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(140), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default="Pending", nullable=False, index=True)
    source_page = db.Column(db.String(120), default="home", nullable=False, index=True)
    ip_address = db.Column(db.String(80))
    active = db.Column(db.Boolean, default=False, nullable=False, index=True)
    archived = db.Column(db.Boolean, default=False, nullable=False, index=True)


class CaseStudy(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "case_studies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    client_industry = db.Column(db.String(120), nullable=False, index=True)
    technologies = db.Column(db.String(300), nullable=False)
    impact = db.Column(db.String(240), nullable=False)
    key_features = db.Column(db.JSON, nullable=False, default=list)
    before_result = db.Column(db.String(240), nullable=False)
    after_result = db.Column(db.String(240), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)


class Job(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False, index=True)
    department = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(140), nullable=False)
    employment_type = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)


class Application(TimestampMixin, db.Model):
    __tablename__ = "job_applications"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(60), nullable=False)
    address = db.Column(db.String(240), nullable=False)
    position = db.Column(db.String(160), nullable=False, index=True)
    experience = db.Column(db.String(80), nullable=False)
    skills = db.Column(db.Text, nullable=False)
    portfolio_url = db.Column(db.String(500))
    cover_letter = db.Column(db.Text, nullable=False)
    resume_filename = db.Column(db.String(255), nullable=False)
    original_resume_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="Received", nullable=False, index=True)


class FaqItem(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "faq_items"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(120), default="General", nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=100, nullable=False, index=True)


class TeamMember(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "team_members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(120), nullable=False, index=True)
    bio = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    linkedin_url = db.Column(db.String(500))
    sort_order = db.Column(db.Integer, default=100, nullable=False, index=True)


class MediaAsset(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "media_assets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(120), default="Brand", nullable=False, index=True)
    source = db.Column(db.String(160), default="External URL", nullable=False)


class SiteSetting(TimestampMixin, PublishMixin, db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), nullable=False, unique=True, index=True)
    label = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    value_text = db.Column(db.Text, nullable=False)
    value_type = db.Column(db.String(30), nullable=False, default="text")
    description = db.Column(db.String(255))


class ChatbotLog(TimestampMixin, db.Model):
    __tablename__ = "chatbot_logs"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(120), nullable=False, index=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(120))
    ip_address = db.Column(db.String(80))


class WebsiteVisit(TimestampMixin, db.Model):
    __tablename__ = "website_visits"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(300), nullable=False, index=True)
    endpoint = db.Column(db.String(120), index=True)
    user_agent = db.Column(db.String(300))
    ip_address = db.Column(db.String(80))


class AuthSessionLog(TimestampMixin, db.Model):
    __tablename__ = "auth_session_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    staff_user_id = db.Column(db.Integer, db.ForeignKey("staff_users.id"), index=True)
    public_user_id = db.Column(db.Integer, db.ForeignKey("public_users.id"), index=True)
    session_identifier = db.Column(db.String(140), nullable=False, index=True)
    ip_address = db.Column(db.String(80))
    user_agent = db.Column(db.String(300))
    device = db.Column(db.String(120))
    browser = db.Column(db.String(120))
    operating_system = db.Column(db.String(120))
    location_label = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    camera_consent = db.Column(db.String(40), default="not-requested", nullable=False)
    camera_image_path = db.Column(db.String(255))
    logged_in_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    logged_out_at = db.Column(db.DateTime(timezone=True))
    success = db.Column(db.Boolean, default=True, nullable=False, index=True)
    suspicious = db.Column(db.Boolean, default=False, nullable=False, index=True)
    failure_reason = db.Column(db.String(255))


class ActivityLog(TimestampMixin, db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_type = db.Column(db.String(20), nullable=False, index=True)
    actor_name = db.Column(db.String(160), nullable=False)
    action = db.Column(db.String(120), nullable=False, index=True)
    resource_type = db.Column(db.String(120), nullable=False, index=True)
    resource_id = db.Column(db.String(120))
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(80))
    user_agent = db.Column(db.String(300))
    staff_user_id = db.Column(db.Integer, db.ForeignKey("staff_users.id"), index=True)
    public_user_id = db.Column(db.Integer, db.ForeignKey("public_users.id"), index=True)
    details = db.Column(db.JSON, nullable=False, default=dict)


class PasswordResetToken(TimestampMixin, db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    public_user_id = db.Column(db.Integer, db.ForeignKey("public_users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    used_at = db.Column(db.DateTime(timezone=True))
    request_ip = db.Column(db.String(80))

    @property
    def is_valid(self) -> bool:
        return not self.used_at and self.expires_at >= utcnow()

    @classmethod
    def default_expiry(cls) -> datetime:
        return utcnow() + timedelta(hours=2)
