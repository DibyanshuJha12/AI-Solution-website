from __future__ import annotations

from datetime import datetime
from pathlib import Path

import psycopg
from flask import Flask, g, request, session
from psycopg import sql
from sqlalchemy.engine import make_url

from config import Config

from .data import (
    BLOGS,
    CASE_STUDIES,
    EVENTS,
    FAQS,
    INDUSTRIES,
    JOBS,
    SERVICES,
    SITE_SETTINGS,
    TEAM_MEMBERS,
    TESTIMONIALS,
    default_blog_content,
    slugify,
)
from .error_handlers import register_error_handlers
from .extensions import csrf, db
from .forms import FeedbackForm
from .models import (
    BlogPost,
    CaseStudy,
    Event,
    FaqItem,
    Industry,
    Job,
    Service,
    SiteSetting,
    TeamMember,
    Testimonial,
    User,
    WebsiteVisit,
    utcnow,
)
from .utils.site import active_settings_map, markdownish
from .utils.schema import synchronize_schema


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(config_class.BASE_DIR / "templates"),
        static_folder=str(config_class.BASE_DIR / "static"),
    )
    app.config.from_object(config_class)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    configure_runtime_database(app)
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    app.config["MEDIA_UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    ensure_database_exists(app)
    db.init_app(app)
    csrf.init_app(app)

    from .routes.admin import admin_bp
    from .routes.api import api_bp
    from .routes.public import public_bp
    from .routes.wireframe import wireframe_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix=app.config["ADMIN_ROUTE_PREFIX"])
    app.register_blueprint(wireframe_bp, url_prefix="/wireframe")
    register_error_handlers(app)

    with app.app_context():
        synchronize_schema()
        seed_database(app)

    @app.before_request
    def load_current_users() -> None:
        from .models import PublicUser

        g.staff_user = None
        g.public_user = None

        staff_user_id = session.get("staff_user_id")
        if staff_user_id:
            g.staff_user = db.session.get(User, staff_user_id)

        public_user_id = session.get("public_user_id")
        if public_user_id:
            g.public_user = db.session.get(PublicUser, public_user_id)

        if request.endpoint and request.endpoint.startswith("static"):
            return
        if request.method == "GET":
            db.session.add(
                WebsiteVisit(
                    path=request.path[:300],
                    endpoint=(request.endpoint or "")[:120],
                    user_agent=(request.user_agent.string or "")[:300],
                    ip_address=(request.headers.get("X-Forwarded-For", request.remote_addr) or "")[:80],
                )
            )
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.debug("Visit tracking skipped", exc_info=True)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            app.config["CONTENT_SECURITY_POLICY"],
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.endpoint and request.endpoint.startswith("admin"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        elif request.endpoint in {"public.login", "public.reset_password", "public.workspace"}:
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response

    @app.context_processor
    def inject_globals() -> dict:
        settings = {}
        try:
            settings = active_settings_map()
        except Exception:
            app.logger.debug("Site settings unavailable", exc_info=True)
        cookie_preference = request.cookies.get(app.config["COOKIE_PREFERENCE_NAME"]) or session.get("cookie_preference", "")
        endpoint = request.endpoint or ""
        cookie_gate_mode = "remember"
        cookie_gate_visible = endpoint.startswith("public") and not cookie_preference
        feedback_form = FeedbackForm(formdata=None)
        feedback_form.source_page.data = request.path

        return {
            "brand_name": "AI SOLUTION",
            "brand_slogan": "SMART SOLUTIONS, INTELLIGENT FUTURE",
            "current_year": datetime.now().year,
            "admin_prefix": app.config["ADMIN_ROUTE_PREFIX"],
            "site_settings": settings,
            "cookie_preference": cookie_preference,
            "cookie_gate_mode": cookie_gate_mode,
            "cookie_gate_visible": cookie_gate_visible,
            "recaptcha_site_key": app.config.get("RECAPTCHA_SITE_KEY", ""),
            "feedback_form": feedback_form,
            "chatbot_prompts": [
                settings.get("chatbot_prompt_one", "Which AI roadmap fits a healthcare provider?"),
                settings.get("chatbot_prompt_two", "How do I start an enterprise automation programme?"),
                settings.get("chatbot_prompt_three", "Show me AI cybersecurity services"),
            ],
        }

    @app.template_filter("date_label")
    def date_label(value) -> str:
        if not value:
            return ""
        return value.strftime("%b %d, %Y")

    @app.template_filter("markdownish")
    def markdownish_filter(value) -> str:
        return markdownish(value)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create database tables and seed production-style starter content."""
        db.create_all()
        seed_database(app)
        print("Database initialized and seeded.")

    @app.cli.command("ensure-postgres-db")
    def ensure_postgres_db_command() -> None:
        """Create the configured PostgreSQL database if the local role can do it."""
        configured_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        database_url = configured_uri if hasattr(configured_uri, "drivername") else make_url(configured_uri)
        if not database_url.drivername.startswith("postgresql"):
            print("Database creation skipped because the configured database is not PostgreSQL.")
            return

        target_database = database_url.database
        if not target_database:
            raise RuntimeError("POSTGRES_DB or DATABASE_URL must include a database name.")

        maintenance_db = "postgres" if target_database != "postgres" else "template1"
        with psycopg.connect(
            host=database_url.host or "localhost",
            port=database_url.port or 5432,
            user=database_url.username,
            password=database_url.password,
            dbname=maintenance_db,
            autocommit=True,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_database,))
                if cursor.fetchone():
                    print(f'PostgreSQL database "{target_database}" already exists.')
                    return
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_database)))
                print(f'PostgreSQL database "{target_database}" created.')

    return app


def configure_runtime_database(app: Flask) -> None:
    configured_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_url = configured_uri if hasattr(configured_uri, "drivername") else make_url(configured_uri)
    driver_name = database_url.drivername

    app.config["DATABASE_RUNTIME_LABEL"] = driver_name
    app.config["DATABASE_RUNTIME_FALLBACK"] = False

    if driver_name.startswith("sqlite"):
        sqlite_path = Path(app.config["SQLITE_DATABASE_PATH"])
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
        return

    if not driver_name.startswith("postgresql"):
        return

    if not app.config.get("DATABASE_FALLBACK_TO_SQLITE", True):
        return

    maintenance_db = database_url.database
    timeout_seconds = int(app.config.get("DATABASE_CONNECT_TIMEOUT_SECONDS", 4))

    try:
        ensure_database_exists(app)
        with psycopg.connect(
            host=database_url.host or "localhost",
            port=database_url.port or 5432,
            user=database_url.username,
            password=database_url.password,
            dbname=maintenance_db,
            connect_timeout=timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception:
        sqlite_path = Path(app.config["SQLITE_DATABASE_PATH"])
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        app.logger.warning(
            "Configured PostgreSQL database is unavailable. Falling back to SQLite at %s.",
            sqlite_path,
        )
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLITE_DATABASE_URI"]
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
        app.config["DATABASE_RUNTIME_LABEL"] = "sqlite-fallback"
        app.config["DATABASE_RUNTIME_FALLBACK"] = True


def ensure_database_exists(app: Flask) -> None:
    configured_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_url = configured_uri if hasattr(configured_uri, "drivername") else make_url(configured_uri)
    if not database_url.drivername.startswith("postgresql"):
        return

    target_database = database_url.database
    if not target_database:
        return

    maintenance_db = "postgres" if target_database != "postgres" else "template1"
    try:
        with psycopg.connect(
            host=database_url.host or "localhost",
            port=database_url.port or 5432,
            user=database_url.username,
            password=database_url.password,
            dbname=maintenance_db,
            autocommit=True,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_database,))
                if cursor.fetchone():
                    return
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_database)))
                app.logger.info('PostgreSQL database "%s" created automatically.', target_database)
    except Exception:
        app.logger.info("Automatic PostgreSQL database check/create skipped.")


def seed_database(app: Flask) -> None:
    refreshable_setting_defaults = {
        "homepage_hero_badge": {
            "Enterprise AI SaaS Studio",
            "London-Based Enterprise AI Studio",
        },
        "homepage_hero_title": {
            "AI SOLUTION",
            "Enterprise AI that turns strategy into operating advantage.",
            "Enterprise AI that turns strategy into measurable advantage.",
        },
        "homepage_hero_text": {
            "Secure automation, analytics, assistants, and intelligent workflows for companies ready to turn AI into measurable operating advantage.",
            "AI SOLUTION designs secure automation, analytics, copilots, and decision systems for organisations that need measurable outcomes, strong governance, and production-ready delivery.",
            "Secure automation, analytics, copilots, and decision systems for teams that want clear governance and visible outcomes.",
        },
        "homepage_video_url": {
            "https://www.youtube.com/embed/_psrFlwA_UU?rel=0",
            "https://www.youtube.com/embed/qYNweeDHiyU?rel=0",
        },
        "solutions_feature_image": {
            "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1400&q=80",
        },
        "careers_hero_image": {
            "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1400&q=80",
        },
        "careers_culture_image": {
            "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1400&q=80",
        },
        "careers_cta_image": {
            "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1400&q=80",
        },
        "contact_phone": {
            "+44 20 3916 8450",
            "+977 9807803733",
            "9807803733",
        },
        "contact_email": {
            "contact@aisolutionsglobal.com",
            "contact@aisolutionsglobal.co.uk",
        },
        "contact_address": {
            "Central London, United Kingdom",
            "Canary Wharf, London, United Kingdom",
        },
        "whatsapp_url": {
            "https://wa.me/447700900123",
            "https://wa.me/9779807803733",
        },
        "chatbot_welcome_message": {
            "Welcome to AI SOLUTION. Tell me your industry or challenge and I will guide you.",
            "Welcome to AI SOLUTION. Share your industry, workflow, or delivery challenge and I will guide you to the strongest next step.",
        },
        "chatbot_prompt_one": {
            "Which AI solution fits a healthcare company?",
            "Which AI roadmap fits a healthcare provider?",
        },
        "chatbot_prompt_two": {
            "How do I start an automation project?",
            "How do I start an enterprise automation programme?",
        },
        "chatbot_prompt_three": {
            "Show me cybersecurity services",
            "Show me AI cybersecurity services",
        },
        "cookie_banner_text": {
            "Essential cookies keep forms, sessions, and security controls working safely. Optional cookies remember preferences and help improve the website experience.",
            "Essential cookies keep forms, sessions, and security controls working safely. Optional preferences remember your choices and support a smoother website experience.",
            "Essential cookies keep forms, sessions, and security controls working safely. Optional preferences can be customized and remembered for a smoother website experience.",
            "Essential cookies keep sessions and forms secure. Optional cookies help remember your preferences and keep the site smoother.",
        },
        "cookie_accept_label": {"Accept", "Accept All"},
        "cookie_decline_label": {"Decline", "Reject Non-Essential"},
        "cookie_manage_label": {"Manage Preferences", "Customize Preferences"},
    }

    if not Service.query.first():
        seeded_services = [Service(**item) for item in SERVICES]
        for service in seeded_services:
            service.publish()
        db.session.add_all(seeded_services)

    if not Industry.query.first():
        seeded_industries = [Industry(**item) for item in INDUSTRIES]
        for industry in seeded_industries:
            industry.publish()
        db.session.add_all(seeded_industries)
    else:
        existing_industries = Industry.query.order_by(Industry.id.asc()).all()
        for record, item in zip(existing_industries, INDUSTRIES):
            record.name = item["name"]
            record.slug = item["slug"]
            record.image_url = item["image_url"]
            record.overview = item["overview"]
            record.problems = item["problems"]
            record.solution = item["solution"]
            record.benefits = item["benefits"]
            record.use_cases = item["use_cases"]
            record.restore()

        if len(existing_industries) < len(INDUSTRIES):
            for item in INDUSTRIES[len(existing_industries) :]:
                industry = Industry(**item)
                industry.publish()
                db.session.add(industry)

        for record in existing_industries[len(INDUSTRIES) :]:
            record.archive()

    if not CaseStudy.query.first():
        seeded_cases = [CaseStudy(**item) for item in CASE_STUDIES]
        for case in seeded_cases:
            case.publish()
        db.session.add_all(seeded_cases)
    else:
        existing_cases = CaseStudy.query.order_by(CaseStudy.id.asc()).all()
        for record, item in zip(existing_cases, CASE_STUDIES):
            record.title = item["title"]
            record.client_industry = item["client_industry"]
            record.technologies = item["technologies"]
            record.impact = item["impact"]
            record.key_features = item.get("key_features", [])
            record.before_result = item["before_result"]
            record.after_result = item["after_result"]
            record.image_url = item["image_url"]
            record.restore()

        if len(existing_cases) < len(CASE_STUDIES):
            for item in CASE_STUDIES[len(existing_cases) :]:
                case = CaseStudy(**item)
                case.publish()
                db.session.add(case)

        for record in existing_cases[len(CASE_STUDIES) :]:
            record.archive()

    if not Testimonial.query.first():
        seeded_testimonials = [Testimonial(**item) for item in TESTIMONIALS]
        for testimonial in seeded_testimonials:
            testimonial.publish()
        db.session.add_all(seeded_testimonials)
    else:
        existing_testimonials = Testimonial.query.order_by(Testimonial.id.asc()).limit(len(TESTIMONIALS)).all()
        for record, item in zip(existing_testimonials, TESTIMONIALS):
            record.customer_name = item["customer_name"]
            record.company_name = item["company_name"]
            record.role = item["role"]
            record.rating = item["rating"]
            record.profile_image = item["profile_image"]
            record.feedback = item["feedback"]
            record.restore()

    if not Event.query.first():
        seeded_events = []
        for item in EVENTS:
            event = Event(
                title=item["title"],
                banner_image=item["banner_image"],
                event_date=item["event_date"],
                event_time=item["event_time"],
                location=item["location"],
                details=item["details"],
            )
            event.publish()
            seeded_events.append(event)
        db.session.add_all(seeded_events)
    else:
        existing_events = Event.query.order_by(Event.id.asc()).all()
        for record, item in zip(existing_events, EVENTS):
            record.title = item["title"]
            record.banner_image = item["banner_image"]
            record.event_date = item["event_date"]
            record.event_time = item["event_time"]
            record.location = item["location"]
            record.details = item["details"]
            record.restore()

        if len(existing_events) < len(EVENTS):
            for item in EVENTS[len(existing_events) :]:
                event = Event(
                    title=item["title"],
                    banner_image=item["banner_image"],
                    event_date=item["event_date"],
                    event_time=item["event_time"],
                    location=item["location"],
                    details=item["details"],
                )
                event.publish()
                db.session.add(event)

        for record in existing_events[len(EVENTS) :]:
            record.archive()

    if not BlogPost.query.first():
        seeded_blogs = []
        images = [item["image_url"] for item in SERVICES]
        authors = ["Maya Ellis", "Arjun Patel", "Grace Morgan", "Leo Chen"]
        for index, (title, category, publish_date) in enumerate(BLOGS):
            post = BlogPost(
                title=title,
                slug=slugify(title),
                image_url=images[index % len(images)],
                description=(
                    "A field guide for executive teams adopting AI with clearer strategy, "
                    "stronger governance, and measurable business outcomes."
                ),
                content=default_blog_content(title, category),
                author=authors[index % len(authors)],
                category=category,
                publish_date=publish_date,
                featured=index < 3,
                meta_title=title,
                meta_description=(
                    "Enterprise AI guidance from AI SOLUTION on delivery strategy, governance, and operational value."
                ),
            )
            post.publish()
            seeded_blogs.append(post)
        db.session.add_all(seeded_blogs)
    else:
        for post in BlogPost.query.all():
            if not post.content:
                post.content = default_blog_content(post.title, post.category)
            if not post.meta_title:
                post.meta_title = post.title
            if not post.meta_description:
                post.meta_description = post.description[:300]

    if not Job.query.first():
        seeded_jobs = []
        for title, department, location, employment_type in JOBS:
            job = Job(
                title=title,
                department=department,
                location=location,
                employment_type=employment_type,
                description=(
                    "Join a focused AI product team building secure automation, analytics, "
                    "and assistant systems for ambitious organizations."
                ),
                requirements=(
                    "Strong communication, production mindset, secure development habits, "
                    "and hands-on experience with modern AI or SaaS delivery."
                ),
            )
            job.publish()
            seeded_jobs.append(job)
        db.session.add_all(seeded_jobs)

    if not FaqItem.query.first():
        seeded_faqs = [FaqItem(**item) for item in FAQS]
        for faq in seeded_faqs:
            faq.publish()
        db.session.add_all(seeded_faqs)

    if not TeamMember.query.first():
        seeded_team = [TeamMember(**item) for item in TEAM_MEMBERS]
        for member in seeded_team:
            member.publish()
        db.session.add_all(seeded_team)
    else:
        existing_team = TeamMember.query.order_by(TeamMember.sort_order.asc(), TeamMember.id.asc()).limit(len(TEAM_MEMBERS)).all()
        for record, item in zip(existing_team, TEAM_MEMBERS):
            record.name = item["name"]
            record.role = item["role"]
            record.bio = item["bio"]
            record.image_url = item["image_url"]
            record.linkedin_url = item["linkedin_url"]
            record.sort_order = item["sort_order"]
            record.restore()

    for item in SITE_SETTINGS:
        setting = SiteSetting.query.filter_by(key=item["key"]).first()
        if not setting:
            setting = SiteSetting(**item)
            setting.publish()
            db.session.add(setting)
            continue

        setting.label = item["label"]
        setting.category = item["category"]
        setting.value_type = item["value_type"]
        setting.description = item["description"]
        refreshable_values = refreshable_setting_defaults.get(item["key"], set())
        if not isinstance(refreshable_values, set):
            refreshable_values = {refreshable_values}
        if not setting.value_text or setting.value_text in refreshable_values:
            setting.value_text = item["value_text"]
        setting.restore()

    admin_user = User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first()
    if not admin_user:
        admin_user = User(
            name="AI SOLUTION Super Admin",
            email=app.config["ADMIN_EMAIL"],
            role="Super Admin",
            is_active=True,
            last_login_at=datetime.now(),
        )
        db.session.add(admin_user)

    admin_user.name = admin_user.name or "AI SOLUTION Super Admin"
    admin_user.role = admin_user.role or "Super Admin"
    admin_user.is_active = True
    admin_user.set_password(app.config["ADMIN_PASSWORD"])

    db.session.commit()
