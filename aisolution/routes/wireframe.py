from __future__ import annotations

from copy import deepcopy
from typing import Any

from flask import Blueprint, abort, render_template, url_for

from ..data import (
    BLOGS,
    CASE_STUDIES,
    EVENTS,
    FAQS,
    INDUSTRIES,
    JOBS,
    PREVIOUS_EVENTS,
    SERVICES,
    TEAM_MEMBERS,
    TESTIMONIALS,
    slugify,
)
from .admin import CONTENT_RESOURCES


wireframe_bp = Blueprint("wireframe", __name__)


GROUP_LABELS = {
    "public": "Public Website",
    "client": "Client Access",
    "admin": "Admin Panel",
    "system": "System Pages",
}

ADMIN_NAV_ITEMS = [
    "Dashboard",
    "Contact Submissions",
    "Users",
    "Applications",
    "RSVPs",
    "Chatbot Logs",
    "Newsletter",
    "Services",
    "Solutions / Industries",
    "Events",
    "Blogs",
    "Testimonials",
    "Feedback",
    "FAQ",
    "Team",
    "Media",
    "Homepage / Privacy / Cookies",
    "Case Studies",
    "Jobs",
    "Security / Auth Logs",
    "Activity Logs",
    "Staff",
]

SOLUTION_CAPABILITIES = [
    {
        "title": "AI Automation",
        "meta": "Automation",
        "copy": "Automate approvals, intake, and repetitive operations with human-in-the-loop controls.",
    },
    {
        "title": "Data Analytics",
        "meta": "Analytics",
        "copy": "Turn fragmented data into trusted dashboards and leadership-ready signals.",
    },
    {
        "title": "Machine Learning",
        "meta": "Prediction",
        "copy": "Build practical ML models for prediction, classification, and optimisation.",
    },
    {
        "title": "AI Chatbots",
        "meta": "Assistant",
        "copy": "Launch branded assistants for support, knowledge access, and guided flows.",
    },
    {
        "title": "Cloud AI Solutions",
        "meta": "Cloud",
        "copy": "Deploy AI securely across cloud, hybrid, and private environments.",
    },
    {
        "title": "Predictive Intelligence",
        "meta": "Forecasting",
        "copy": "Forecast demand, risk, churn, and performance before issues surface.",
    },
    {
        "title": "Business Intelligence",
        "meta": "Decision",
        "copy": "Create governed BI hubs with natural-language insight and executive KPIs.",
    },
    {
        "title": "AI Security Systems",
        "meta": "Security",
        "copy": "Strengthen cyber operations with threat enrichment and risk scoring.",
    },
]


def truncate(text: str | None, limit: int = 120) -> str:
    if not text:
        return ""
    value = " ".join(str(text).split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def wf_section(kind: str, label: str, summary: str = "", **kwargs) -> dict[str, Any]:
    section = {"kind": kind, "label": label, "summary": summary}
    section.update(kwargs)
    return section


def wf_page(
    group: str,
    slug: str,
    title: str,
    summary: str,
    *,
    live_endpoint: str | None = None,
    live_values: dict[str, Any] | None = None,
    sections: list[dict[str, Any]] | None = None,
    accent: str = "slate",
) -> dict[str, Any]:
    return {
        "group": group,
        "slug": slug,
        "title": title,
        "summary": summary,
        "live_endpoint": live_endpoint,
        "live_values": live_values or {},
        "sections": sections or [],
        "accent": accent,
    }


def service_cards(limit: int | None = None) -> list[dict[str, Any]]:
    items = SERVICES[:limit] if limit else SERVICES
    return [
        {
            "title": item["title"],
            "meta": item["category"],
            "copy": truncate(item["description"], 92),
            "visual": item["icon"],
            "chips": [item["category"]],
        }
        for item in items
    ]


def industry_cards(limit: int | None = None) -> list[dict[str, Any]]:
    items = INDUSTRIES[:limit] if limit else INDUSTRIES
    return [
        {
            "title": item["name"],
            "meta": item["slug"].replace("-", " ").title(),
            "copy": truncate(item["overview"], 104),
            "visual": item["name"],
            "chips": list(item["benefits"][:2]),
            "note": truncate(item["solution"], 92),
        }
        for item in items
    ]


def industry_program_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": item["name"],
            "meta": f"{len(item['use_cases'])} use cases",
            "copy": truncate(item["overview"], 94),
            "visual": item["name"],
            "chips": list(item["use_cases"][:2]),
            "note": truncate(item["problems"], 90),
            "support": truncate(item["solution"], 110),
        }
        for item in INDUSTRIES
    ]


def case_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": item["title"],
            "meta": item["client_industry"],
            "copy": truncate(item["impact"], 92),
            "visual": item["client_industry"],
            "chips": [tech.strip() for tech in item["technologies"].split(",")[:2]],
            "before": item["before_result"],
            "after": item["after_result"],
        }
        for item in CASE_STUDIES
    ]


def testimonial_cards(limit: int | None = None) -> list[dict[str, Any]]:
    items = TESTIMONIALS[:limit] if limit else TESTIMONIALS
    return [
        {
            "title": item["customer_name"],
            "meta": f"{item['role']} · {item['company_name']}",
            "copy": truncate(item["feedback"], 110),
            "rating": item["rating"],
            "visual": item["company_name"],
        }
        for item in items
    ]


def event_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": item["title"],
            "meta": item["event_date"].strftime("%b %d, %Y"),
            "copy": truncate(item["details"], 104),
            "visual": item["category"],
            "chips": [item["format_label"], item["location"]],
            "date": item["event_time"],
        }
        for item in items
    ]


def previous_event_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": item["title"],
            "meta": item["category"],
            "copy": truncate(item["details"], 104),
            "visual": item["status_badge"],
            "chips": list(item["highlights"][:2]),
            "date": item["event_date"].strftime("%b %d, %Y"),
            "location": item["location"],
        }
        for item in PREVIOUS_EVENTS
    ]


def blog_cards(limit: int | None = None) -> list[dict[str, Any]]:
    items = BLOGS[:limit] if limit else BLOGS
    cards = []
    for title, category, publish_date in items:
        cards.append(
            {
                "title": title,
                "meta": category,
                "copy": "Featured editorial insight for enterprise teams.",
                "visual": category,
                "date": publish_date.strftime("%b %d, %Y"),
            }
        )
    return cards


def job_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": title,
            "meta": department,
            "copy": f"{location} · {employment_type}",
            "visual": department,
        }
        for title, department, location, employment_type in JOBS
    ]


def team_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": member["name"],
            "meta": member["role"],
            "copy": truncate(member["bio"], 104),
            "visual": member["name"],
        }
        for member in TEAM_MEMBERS
    ]


def faq_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": item["question"],
            "copy": truncate(item["answer"], 128),
            "meta": item["category"],
        }
        for item in FAQS
    ]


def build_public_pages() -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []

    pages.append(
        wf_page(
            "public",
            "home",
            "Homepage",
            "Hero, stats band, company introduction, featured services, video brief, testimonials, team, blog and event previews, FAQ, CTA.",
            live_endpoint="public.home",
            sections=[
                wf_section(
                    "hero",
                    "Hero",
                    "Opening story, proof strip, and CTA pair.",
                    eyebrow="Enterprise AI SaaS Studio",
                    title="Enterprise AI that turns strategy into measurable advantage.",
                    description="Secure automation, analytics, copilots, and decision systems for teams that want clear governance and visible outcomes.",
                    badges=["Secure-by-design delivery", "AI-guided business experiences", "Enterprise advisory and build delivery"],
                    actions=["Book Strategy Session", "Explore Industry Solutions"],
                    visual={
                        "title": "Discovery to production",
                        "summary": "Use-case design, governed rollout, and measurable adoption planning.",
                        "items": [
                            "Secure deployment architecture",
                            "Board-ready performance reporting",
                            "AI-guided enterprise workflows",
                        ],
                    },
                ),
                wf_section(
                    "metrics",
                    "Stats Band",
                    "Short proof points from the homepage strip.",
                    metrics=[
                        {"value": "72", "label": "AI workflows shipped"},
                        {"value": "41%", "label": "Average process acceleration"},
                        {"value": "18", "label": "Industries supported"},
                        {"value": "99%", "label": "Target platform uptime"},
                    ],
                ),
                wf_section(
                    "split",
                    "Company Introduction",
                    "Mission and vision blocks.",
                    left={
                        "eyebrow": "Company Introduction",
                        "title": "AI operating systems for teams that need dependable execution.",
                        "copy": "AI SOLUTION helps organisations modernise operations with secure assistants, decision intelligence, workflow orchestration, and practical AI delivery shaped around governance and measurable outcomes.",
                    },
                    right=[
                        {
                            "title": "Mission",
                            "meta": "Purpose",
                            "copy": "Make enterprise AI practical, secure, and commercially useful.",
                        },
                        {
                            "title": "Vision",
                            "meta": "Future state",
                            "copy": "A future where every team has trusted AI support for faster, clearer decisions.",
                        },
                    ],
                ),
                wf_section(
                    "grid",
                    "Featured Services",
                    "Four compact service cards from the homepage.",
                    columns=4,
                    cards=service_cards(limit=4),
                ),
                wf_section(
                    "split",
                    "AI Transformation Brief",
                    "The video briefing plus two insight cards.",
                    left={
                        "eyebrow": "AI Transformation Brief",
                        "title": "See how modern AI reshapes the operating model.",
                        "copy": "A short executive briefing for leaders exploring automation, copilots, analytics, cyber resilience, and enterprise intelligence.",
                        "cards": [
                            {
                                "title": "Enterprise Focus",
                                "copy": "Clear strategy for teams aligning AI with delivery and governance.",
                            },
                            {
                                "title": "Operational Value",
                                "copy": "Practical examples of how AI improves workflows, decisions, and service quality.",
                            },
                        ],
                    },
                    right={
                        "title": "Video placeholder",
                        "summary": "Embedded briefing block on the live site.",
                        "items": ["Executive briefing frame", "Autoplay-disabled video slot", "Responsive media shell"],
                    },
                ),
                wf_section(
                    "rail",
                    "Trusted Feedback",
                    "Testimonial carousel plus the summary metrics strip.",
                    metrics=[
                        {"value": "4.9", "label": "Average Rating"},
                        {"value": str(len(TESTIMONIALS) + len(FAQS)), "label": "Total Feedback"},
                        {"value": str(len(TESTIMONIALS)), "label": "Approved Feedback"},
                        {"value": str(len(TESTIMONIALS)), "label": "Testimonials"},
                    ],
                    cards=testimonial_cards(limit=4),
                ),
                wf_section(
                    "grid",
                    "Meet Our Team",
                    "Three leadership cards with social links.",
                    columns=3,
                    cards=team_cards(),
                ),
                wf_section(
                    "split",
                    "Latest Articles and Upcoming Events",
                    "Two preview panels at the bottom of the homepage.",
                    left={
                        "eyebrow": "Latest Articles",
                        "cards": blog_cards(limit=3),
                    },
                    right={
                        "eyebrow": "Upcoming Events",
                        "cards": event_cards(EVENTS[:3]),
                    },
                ),
                wf_section(
                    "legal",
                    "FAQ",
                    "Accordion-style questions and answers from the homepage.",
                    cards=faq_cards(),
                ),
                wf_section(
                    "cta",
                    "CTA Panel",
                    "Final action strip for contact and events.",
                    title="Plan the right AI delivery path before your team commits budget and time.",
                    copy="Use a secure inquiry to brief AI SOLUTION on your workflow, industry, governance needs, and transformation goals.",
                    actions=["Start Inquiry", "Reserve an AI Event"],
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "solutions",
            "Solutions",
            "Solution studio, service catalog, industry index, and industry programme gallery.",
            live_endpoint="public.solutions",
            sections=[
                wf_section(
                    "hero",
                    "Solutions Hero",
                    "Opening split hero with trust strip and visual card.",
                    eyebrow="Solutions + Industries",
                    title="AI systems for workflows, industries, decisions, and security.",
                    description="A compact view of the capabilities and sector programmes we use to turn AI strategy into delivery.",
                    badges=["Use-case to production mapping", "Governed enterprise rollout", "Measurable transformation value"],
                    actions=["Explore Capabilities", "Review Industries"],
                    visual={
                        "title": "Enterprise AI operating layers",
                        "summary": "Automation, decision intelligence, governed copilots, and secure workflow orchestration.",
                        "items": ["Cross-functional rollout", "Guided advisory flows", "Production-ready experiences"],
                    },
                ),
                wf_section(
                    "grid",
                    "Solution Studio",
                    "Eight capability cards from the live page.",
                    columns=4,
                    cards=SOLUTION_CAPABILITIES,
                ),
                wf_section(
                    "grid",
                    "Solution Catalog",
                    "The main service catalogue grid and filter bar.",
                    columns=4,
                    cards=service_cards(),
                ),
                wf_section(
                    "grid",
                    "Industry Index",
                    "A compact strip of sector entry points.",
                    columns=4,
                    cards=industry_cards(),
                ),
                wf_section(
                    "grid",
                    "Industry Programme Gallery",
                    "Expanded cards with problems, solution focus, and use cases.",
                    columns=2,
                    cards=industry_program_cards(),
                ),
                wf_section(
                    "cta",
                    "Industry CTA",
                    "Final action strip from the solutions page.",
                    title="Map your industry, workflow, and risk posture to the right AI delivery path.",
                    copy="We help leadership teams prioritise the first use case, shape governance, and move from concept to production with confidence.",
                    actions=["Speak With AI SOLUTION", "Review Case Studies"],
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "industries",
            "Industry Stack",
            "The standalone industry stack view that currently resolves from the solutions page anchor.",
            live_endpoint="public.industries",
            sections=[
                wf_section(
                    "hero",
                    "Industry Hero",
                    "The dedicated industry overview from the redirecting route.",
                    eyebrow="Industry-Specific AI",
                    title="Practical AI architecture for the realities of each market.",
                    description="Each industry programme combines discovery, secure implementation, adoption, and measurable improvement.",
                    badges=["Sector-led delivery", "Outcome-focused architecture", "Practical adoption path"],
                    actions=["Open Solutions Anchor", "Contact Us"],
                    visual={
                        "title": "Industry focus",
                        "summary": "One page of market-specific AI programmes.",
                        "items": ["Healthcare", "Finance", "Education", "Retail", "Cybersecurity", "Data Analytics", "Automation", "Cloud & DevOps"],
                    },
                ),
                wf_section(
                    "stack",
                    "Industry Stack",
                    "One row per sector with problem, solution, benefits, and use cases.",
                    cards=industry_program_cards(),
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "portfolio",
            "Portfolio",
            "Hero split plus compact case study grid.",
            live_endpoint="public.portfolio",
            sections=[
                wf_section(
                    "hero",
                    "Portfolio Hero",
                    "Case-study introduction with trust strip and visual card.",
                    eyebrow="Portfolio & Case Studies",
                    title="Practical AI delivery patterns with measurable impact.",
                    description="Browse compact case studies across healthcare, finance, retail, logistics, education, and operations.",
                    badges=["Delivery stories with measurable results", "Secure AI implementation patterns", "Executive-friendly outcomes"],
                    actions=["Explore Case Studies", "Discuss Your Programme"],
                    visual={
                        "title": "Enterprise transformation visuals",
                        "summary": "Analytics, automation, risk monitoring, cloud intelligence, and sector rollout patterns.",
                        "items": ["AI strategy", "Decision intelligence", "Secure delivery"],
                    },
                ),
                wf_section(
                    "grid",
                    "Case Studies",
                    "The live portfolio cards.",
                    columns=2,
                    cards=case_cards(),
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "testimonials",
            "Testimonials",
            "Hero split, client stories, carousel, and confidence section.",
            live_endpoint="public.testimonials",
            sections=[
                wf_section(
                    "hero",
                    "Customer Voices Hero",
                    "The trust-focused opening layout from the testimonial page.",
                    eyebrow="Customer Voices",
                    title="Trusted by leaders who wanted AI delivery to feel calm and production-ready.",
                    description="Practical architecture, secure implementation, and measurable outcomes for organisations that need enterprise-ready AI execution.",
                    badges=["Secure implementation", "Executive-ready communication", "Measurable adoption"],
                    actions=["Share Your Feedback", "Discuss a Similar Engagement"],
                    visual={
                        "title": "Client Trust",
                        "summary": "Feedback from teams that needed dependable AI execution.",
                        "items": ["Average rating", "Verified reviews", "Approved feedback", "Testimonials"],
                    },
                ),
                wf_section(
                    "split",
                    "Client Stories",
                    "Featured review card and review snapshot panel.",
                    left={
                        "eyebrow": "Featured Review",
                        "cards": testimonial_cards(limit=1),
                    },
                    right={
                        "eyebrow": "Review Snapshot",
                        "cards": [
                            {
                                "title": "Security-first implementation",
                                "copy": "Programmes are designed with governance, traceability, and operational safeguards built in.",
                            },
                            {
                                "title": "Executive-ready communication",
                                "copy": "Leaders receive clear progress, practical recommendations, and measurable outcomes.",
                            },
                            {
                                "title": "Useful adoption in real teams",
                                "copy": "Solutions are shaped around how people actually work, so assistants and automation become part of daily operations.",
                            },
                        ],
                    },
                ),
                wf_section(
                    "rail",
                    "Testimonial Carousel",
                    "Auto-scrolling cards in the live UI.",
                    cards=testimonial_cards(),
                ),
                wf_section(
                    "grid",
                    "Why Clients Stay",
                    "Three confidence-building cards.",
                    columns=3,
                    cards=[
                        {
                            "title": "Security-first implementation",
                            "copy": "Governance, traceability, and safeguards are built into the delivery model.",
                        },
                        {
                            "title": "Executive-ready communication",
                            "copy": "Progress stays clear and measurable instead of abstract or overly technical.",
                        },
                        {
                            "title": "Useful adoption in real teams",
                            "copy": "Systems are shaped around how people actually work, so adoption feels practical.",
                        },
                    ],
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "events",
            "Events",
            "Hero, featured event, events grid, previous events, and RSVP form.",
            live_endpoint="public.events",
            sections=[
                wf_section(
                    "hero",
                    "Events Hero",
                    "The opening event-lab hero with CTA buttons and metrics.",
                    eyebrow="AI Events",
                    title="AI events and innovation programs.",
                    description="Compact conferences, workshops, bootcamps, webinars, and innovation sessions for enterprise teams.",
                    badges=["Enterprise event design", "Secure verified registration", "Responsive on every device"],
                    actions=["Register Now", "Explore Events"],
                    visual={
                        "title": "Featured Event",
                        "summary": EVENTS[0]["title"],
                        "items": [
                            EVENTS[0]["event_date"].strftime("%b %d, %Y"),
                            EVENTS[0]["event_time"],
                            EVENTS[0]["location"],
                        ],
                    },
                ),
                wf_section(
                    "grid",
                    "Explore Events",
                    "Eight compact event cards.",
                    columns=2,
                    cards=event_cards(EVENTS),
                ),
                wf_section(
                    "grid",
                    "Previous Events",
                    "Archived event cards and highlights.",
                    columns=2,
                    cards=previous_event_cards(),
                ),
                wf_section(
                    "form",
                    "Event Registration",
                    "One RSVP flow with security checks.",
                    intro={
                        "eyebrow": "Event Registration",
                        "title": "One clear registration flow built for fast confirmation.",
                        "copy": "The form stays simple while the backend validates details, prevents duplicates, and stores registrations securely.",
                        "cards": [
                            {
                                "title": "Secure submission handling",
                                "copy": "Validated submission, duplicate request protection, and reliable record keeping stay active.",
                            },
                            {
                                "title": "Responsive on every device",
                                "copy": "Balanced spacing, clear labels, and theme support keep the flow polished everywhere.",
                            },
                        ],
                    },
                    fields=[
                        "Full Name",
                        "Email",
                        "Phone",
                        "Company",
                        "Event",
                        "Message",
                        "Captcha",
                        "Terms checkbox",
                    ],
                    submit_label="Submit Registration",
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "blog",
            "Blog",
            "Editorial hero, featured insight, and latest posts grid.",
            live_endpoint="public.blog",
            sections=[
                wf_section(
                    "hero",
                    "Blog Hero",
                    "Editorial introduction and premium trust strip.",
                    eyebrow="AI Articles",
                    title="Guides for automation, intelligence, security, and transformation.",
                    description="Field-tested thinking for companies building AI programs with discipline.",
                    badges=["Premium editorial layout", "Practical reading-time guidance", "Executive AI insights"],
                ),
                wf_section(
                    "grid",
                    "Featured Insight",
                    "The lead blog card from the current feed.",
                    columns=1,
                    cards=blog_cards(limit=1),
                ),
                wf_section(
                    "grid",
                    "Latest Posts",
                    "The rest of the blog cards in a compact magazine layout.",
                    columns=2,
                    cards=blog_cards()[1:],
                ),
            ],
        )
    )

    blog_slug = slugify(BLOGS[0][0])
    pages.append(
        wf_page(
            "public",
            "blog-detail",
            "Blog Detail",
            "Hero meta strip, article body, share bar, comments, related posts.",
            live_endpoint="public.blog_detail",
            live_values={"slug": blog_slug},
            sections=[
                wf_section(
                    "hero",
                    "Article Hero",
                    "Title, category, author, publish date, and reading time.",
                    eyebrow=BLOGS[0][1],
                    title=BLOGS[0][0],
                    description="The article page opens with a compact hero and meta row before the long-form content begins.",
                    badges=["Author", "Publish date", "Read time"],
                ),
                wf_section(
                    "split",
                    "Article Body",
                    "Share bar, rich copy, and a reader discussion preview.",
                    left={
                        "eyebrow": "Share this insight",
                        "title": "Article content",
                        "copy": "The live page renders a structured article, share actions, and a comment preview under the main copy.",
                        "cards": [
                            {"title": "Executive Snapshot", "copy": "Why the topic matters for enterprise AI programmes."},
                            {"title": "What Leaders Should Solve First", "copy": "The first decisions that shape successful delivery."},
                            {"title": "Delivery Approach", "copy": "Discovery, architecture, pilot validation, and controlled rollout."},
                            {"title": "Governance Considerations", "copy": "Approval paths, human review points, and escalation rules."},
                            {"title": "Where AI SOLUTION Helps", "copy": "How the team turns strategy into a delivery path."},
                            {"title": "Recommended Next Step", "copy": "Use the contact form to define the first implementation path."},
                        ],
                    },
                    right={
                        "eyebrow": "Comments",
                        "cards": [
                            {
                                "title": "Operations Lead",
                                "copy": "Useful because it keeps governance and rollout planning in the same conversation.",
                            },
                            {
                                "title": "Technology Director",
                                "copy": "The practical framing around adoption and measurable outcomes is the right lens.",
                            },
                            {
                                "title": "Service Transformation Manager",
                                "copy": "The link between workflow design and trust is the part teams often miss.",
                            },
                        ],
                    },
                ),
                wf_section(
                    "split",
                    "Related Posts",
                    "Sidebar related-post cards and the final CTA.",
                    left={
                        "eyebrow": "Related Articles",
                        "cards": blog_cards(limit=3)[1:],
                    },
                    right={
                        "eyebrow": "Need a delivery partner?",
                        "title": "Turn strategy into a production roadmap.",
                        "copy": "Share your workflow, security requirements, and target outcome to get a focused recommendation.",
                    },
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "careers",
            "Careers",
            "Career hero, culture, benefits, CTA strip, job cards, process, and application form.",
            live_endpoint="public.careers",
            sections=[
                wf_section(
                    "hero",
                    "Careers Hero",
                    "A split hero with workplace visual and trust strip.",
                    eyebrow="Careers",
                    title="Build secure AI products with a team that cares about craft.",
                    description="Join AI SOLUTION to design intelligent systems used by real businesses across industries, with strong engineering discipline and responsible AI delivery at the center.",
                    badges=["Product-minded teams", "Secure engineering culture", "Enterprise AI delivery"],
                    actions=["View Open Roles", "Apply Securely"],
                    visual={
                        "title": "Why people join",
                        "summary": "Teams work across strategy, design, engineering, automation, analytics, and client delivery.",
                        "items": ["Hybrid-first collaboration", "Continuous AI learning budget", "Security-led engineering standards", "Wellbeing and support culture"],
                    },
                ),
                wf_section(
                    "split",
                    "Culture",
                    "Culture block and benefits chip list.",
                    left={
                        "eyebrow": "Culture",
                        "title": "Focused, collaborative, security-aware, and product-minded.",
                        "copy": "We value calm execution, clear communication, thoughtful design, and responsible AI delivery.",
                    },
                    right={
                        "eyebrow": "Benefits",
                        "cards": [
                            {
                                "title": "AI learning and experimentation",
                                "copy": "Structured time for research, prompt engineering, and platform improvement.",
                            },
                            {
                                "title": "Supportive team environment",
                                "copy": "Clear reviews, calm problem-solving, and mentoring across disciplines.",
                            },
                            {
                                "title": "High-impact enterprise work",
                                "copy": "Automation, analytics, assistants, and security programmes that matter.",
                            },
                        ],
                    },
                ),
                wf_section(
                    "grid",
                    "Open Roles",
                    "Eight job cards in a compact grid.",
                    columns=2,
                    cards=job_cards(),
                ),
                wf_section(
                    "timeline",
                    "Hiring Process",
                    "Four clear hiring stages.",
                    steps=[
                        {"title": "Application review", "copy": "We review role fit, communication, and relevant experience."},
                        {"title": "Team conversation", "copy": "You meet the people closest to the role and delivery context."},
                        {"title": "Practical assessment", "copy": "A focused exercise that reflects real product or engineering work."},
                        {"title": "Offer and onboarding", "copy": "Clear expectations, structured onboarding, and fast access to tools."},
                    ],
                ),
                wf_section(
                    "form",
                    "Application Form",
                    "Resume upload and secure submission flow.",
                    intro={
                        "eyebrow": "Secure Application",
                        "title": "Apply to AI SOLUTION",
                        "copy": "Resume files are validated, protected, and reviewed through a secure internal hiring workflow.",
                        "cards": [
                            {
                                "title": "What to expect",
                                "copy": "We look for thoughtful problem-solvers who communicate clearly and care about building secure systems.",
                            }
                        ],
                    },
                    fields=[
                        "Full Name",
                        "Email",
                        "Phone",
                        "Address",
                        "Position",
                        "Experience",
                        "Skills",
                        "Portfolio URL",
                        "Cover Letter",
                        "Resume Upload",
                        "Captcha",
                        "Terms checkbox",
                    ],
                    submit_label="Submit Application",
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "contact",
            "Contact Us",
            "Hero split, contact cards, social links, inquiry form, and map section.",
            live_endpoint="public.contact",
            sections=[
                wf_section(
                    "hero",
                    "Contact Hero",
                    "The opening contact story and trust strip.",
                    eyebrow="Contact Us",
                    title="Start a secure AI conversation with our delivery team.",
                    description="Share your operating context and we will recommend the clearest next step for automation, analytics, support, cloud AI, or cybersecurity.",
                    badges=["Business-first consultation", "Secure enquiry handling", "Enterprise AI roadmap support"],
                    visual={
                        "title": "Premium AI-business support",
                        "summary": "Strategy workshops, secure cloud intelligence, automation planning, analytics mapping, and practical delivery guidance.",
                        "items": ["Smart support", "Fast response path", "Delivery planning"],
                    },
                ),
                wf_section(
                    "grid",
                    "Contact Methods",
                    "Phone, email, office, and social cards.",
                    columns=2,
                    cards=[
                        {"title": "Phone", "copy": "+977 9807803733", "meta": "Direct line"},
                        {"title": "Email", "copy": "contact@aisolutionsglobal.co.uk", "meta": "Business inbox"},
                        {"title": "Office", "copy": "Canary Wharf, London, United Kingdom", "meta": "Executive workshop space"},
                        {"title": "LinkedIn", "copy": "Leadership updates and partnerships", "meta": "External link"},
                    ],
                ),
                wf_section(
                    "form",
                    "Inquiry Form",
                    "The multi-field contact form from the live site.",
                    intro={
                        "eyebrow": "Contact Form",
                        "title": "Share project context, service interest, and budget range.",
                        "copy": "The form keeps the same field order as the live page and includes the terms checkbox and captcha challenge.",
                    },
                    fields=[
                        "Full Name",
                        "Email",
                        "Subject",
                        "Phone",
                        "Company",
                        "Country",
                        "Job Title",
                        "Service",
                        "Contact Method",
                        "Budget",
                        "Message",
                        "Captcha",
                        "Terms checkbox",
                    ],
                    submit_label="Send Inquiry",
                ),
                wf_section(
                    "split",
                    "Get Directions",
                    "Office location plus map frame.",
                    left={
                        "eyebrow": "Get Directions",
                        "title": "Visit our Canary Wharf AI strategy studio.",
                        "copy": "We support global clients remotely and host executive workshops from our London base for discovery, delivery planning, solution mapping, and board-level AI strategy sessions.",
                    },
                    right={
                        "eyebrow": "Map frame",
                        "title": "Interactive map placeholder",
                        "copy": "The live page embeds a Google Maps frame beside the directions card.",
                    },
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "client",
            "login",
            "Client Login",
            "Intro, security trust grid, and three auth panels.",
            live_endpoint="public.login",
            sections=[
                wf_section(
                    "hero",
                    "Client Access Intro",
                    "The opening hero from the client login page.",
                    eyebrow="Secure Access",
                    title="Client Workspace Access",
                    description="Sign in, create an account, or request a password reset through a protected enterprise-ready flow designed for approved clients and business contacts.",
                    badges=["Protected sessions", "Custom numeric CAPTCHA", "Privacy-first access"],
                ),
                wf_section(
                    "grid",
                    "Security Trust Grid",
                    "Three trust cards directly under the intro copy.",
                    columns=3,
                    cards=[
                        {"title": "Protected Sessions", "copy": "Secure session handling, route protection, and suspicious login monitoring."},
                        {"title": "Custom Numeric CAPTCHA", "copy": "Dynamic challenge validation with refresh-after-failure protection."},
                        {"title": "Privacy-First Access", "copy": "Account flows are designed around consent, validation, and business-only use."},
                    ],
                ),
                wf_section(
                    "auth",
                    "Auth Panels",
                    "Login, create-account, and forgot-password states.",
                    panels=[
                        {
                            "title": "Login",
                            "copy": "Email, password, remember device, numeric CAPTCHA, and continue button.",
                            "fields": ["Email", "Password", "Remember this device", "Captcha"],
                        },
                        {
                            "title": "Create Account",
                            "copy": "Full name, company, email, password confirmation, privacy checkbox, and captcha.",
                            "fields": ["Full Name", "Company", "Email", "Password", "Confirm Password", "Remember this device", "Privacy checkbox", "Captcha"],
                        },
                        {
                            "title": "Forgot Password",
                            "copy": "Single email field with secure reset-path generation.",
                            "fields": ["Email", "Captcha"],
                        },
                    ],
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "client",
            "reset-password",
            "Reset Password",
            "Single-purpose secure reset form.",
            live_endpoint=None,
            sections=[
                wf_section(
                    "form",
                    "Reset Form",
                    "Two password fields and the challenge widget.",
                    intro={
                        "eyebrow": "Password Reset",
                        "title": "Create a new secure password",
                        "copy": "Choose a strong password to complete your account recovery.",
                    },
                    fields=["New Password", "Confirm Password", "Captcha"],
                    submit_label="Update Password",
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "client",
            "workspace",
            "Workspace",
            "Client dashboard with metrics and next-step panel.",
            live_endpoint="public.workspace",
            sections=[
                wf_section(
                    "hero",
                    "Workspace Hero",
                    "A simple welcome banner for signed-in clients.",
                    eyebrow="Client Workspace",
                    title="Welcome back, client.",
                    description="Your secure workspace keeps project communication, intake, and next-step planning organized and accessible.",
                    badges=["Protected session controls", "Tracked account activity", "Secure route handling"],
                ),
                wf_section(
                    "metrics",
                    "Account Metrics",
                    "Four quick stats from the client dashboard.",
                    metrics=[
                        {"value": "Account email", "label": "Profile data"},
                        {"value": "Company", "label": "Organisation"},
                        {"value": "Inquiries", "label": "Submitted enquiries"},
                        {"value": "Assistant sessions", "label": "Chatbot activity"},
                    ],
                ),
                wf_section(
                    "split",
                    "Next Steps",
                    "The route keeps a small action panel and a security card.",
                    left={
                        "eyebrow": "Next Steps",
                        "title": "Keep delivery moving with secure communication.",
                        "copy": "Use the contact pathway for scoped requests, explore current solution areas, or continue using the assistant for high-level guidance before a formal engagement review.",
                    },
                    right={
                        "eyebrow": "Account Security",
                        "title": "Protected session controls are active.",
                        "copy": "Account access is tracked with session logging, numerical verification, and protected route handling.",
                    },
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "privacy",
            "Privacy Policy",
            "Hero, table of contents, and structured policy sections.",
            live_endpoint="public.privacy",
            sections=[
                wf_section(
                    "hero",
                    "Privacy Hero",
                    "The policy introduction and consent-oriented trust strip.",
                    eyebrow="Privacy Policy",
                    title="Clear privacy information for AI SOLUTION visitors, clients, applicants, and event guests.",
                    description="This notice explains how AI SOLUTION handles personal data under the UK GDPR, the Data Protection Act 2018, and PECR where cookies are used.",
                    badges=["UK GDPR-focused privacy notice", "Covers chatbot, forms, and consent", "Structured for clear review"],
                ),
                wf_section(
                    "legal",
                    "Policy Sections",
                    "The legal page table of contents and article outline.",
                    toc=[
                        "Who we are",
                        "Data we collect",
                        "How we use data",
                        "Lawful bases",
                        "AI chatbot data usage",
                        "Cookies and consent",
                        "Sharing and transfers",
                        "Retention",
                        "Your rights",
                        "Security",
                        "Contact and complaints",
                    ],
                    sections=[
                        {"title": "Who we are", "copy": "Controller information and privacy contact details."},
                        {"title": "Data we collect", "copy": "Identity, enquiry, recruitment, login, and technical records."},
                        {"title": "How we use data", "copy": "Responding, security, communications, and service improvement."},
                        {"title": "Lawful bases", "copy": "Legitimate interests, contract, consent, and legal obligation."},
                        {"title": "AI chatbot data usage", "copy": "Server-side logging, model support, and abuse monitoring."},
                        {"title": "Cookies and consent", "copy": "Essential cookies plus preference handling and consent banner flows."},
                        {"title": "Sharing and transfers", "copy": "Service providers and safeguards for international processing."},
                        {"title": "Retention", "copy": "Retention windows for enquiries, events, applications, logs, and newsletters."},
                        {"title": "Your rights", "copy": "Access, correction, erasure, objection, portability, and consent withdrawal."},
                        {"title": "Security", "copy": "Password hashing, session handling, validation, file controls, and logging."},
                        {"title": "Contact and complaints", "copy": "Privacy questions and the ICO complaint path."},
                    ],
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "public",
            "terms",
            "Terms & Conditions",
            "Hero, table of contents, and structured terms sections.",
            live_endpoint="public.terms",
            sections=[
                wf_section(
                    "hero",
                    "Terms Hero",
                    "The terms introduction and review strip.",
                    eyebrow="Terms & Conditions",
                    title="Clear terms for using the AI SOLUTION website and services.",
                    description="These terms explain how to use the website, what happens when you submit an enquiry, and the limits that apply to our content and services.",
                    badges=["Clear usage rules", "Detailed but concise", "Easy to review"],
                ),
                wf_section(
                    "legal",
                    "Terms Sections",
                    "The terms page table of contents and article outline.",
                    toc=[
                        "Website use",
                        "Enquiries and submissions",
                        "Services and statements of work",
                        "Acceptable conduct",
                        "Content and intellectual property",
                        "Privacy and cookies",
                        "Third-party tools and links",
                        "Liability and warranties",
                        "Updates and contact",
                    ],
                    sections=[
                        {"title": "Website use", "copy": "Lawful browsing, prohibited misuse, and security boundaries."},
                        {"title": "Enquiries and submissions", "copy": "Forms do not create a contract, booking, or hiring commitment by themselves."},
                        {"title": "Services and statements of work", "copy": "Commercial commitments are confirmed separately in writing."},
                        {"title": "Acceptable conduct", "copy": "Honesty, no abuse, and no disruption or impersonation."},
                        {"title": "Content and intellectual property", "copy": "Branding, layouts, and content remain protected."},
                        {"title": "Privacy and cookies", "copy": "Privacy policy governs data handling and consent."},
                        {"title": "Third-party tools and links", "copy": "External services are governed by their own notices and terms."},
                        {"title": "Liability and warranties", "copy": "Website content is informational and provided as available."},
                        {"title": "Updates and contact", "copy": "Terms may change; questions go to the contact inbox."},
                    ],
                ),
            ],
        )
    )

    pages.append(
        wf_page(
            "system",
            "error",
            "Error State",
            "The generic system message template used by the error handler.",
            live_endpoint=None,
            sections=[
                wf_section(
                    "hero",
                    "System Message",
                    "The error page keeps the navigation context and recovery actions visible.",
                    eyebrow="System Message",
                    title="We can still get you to the right place.",
                    description="Use the main navigation to continue browsing, or contact AI SOLUTION directly if you were trying to reach a team member or request support.",
                    badges=["Route recovery", "Support fallback", "Noindex system page"],
                ),
                wf_section(
                    "split",
                    "Recovery Options",
                    "Two-column recovery block.",
                    left={
                        "eyebrow": "Need help quickly?",
                        "title": "Continue using the site.",
                        "copy": "The header, footer, and navigation remain available so the user can keep moving without losing context.",
                    },
                    right={
                        "eyebrow": "Status",
                        "title": "Error response",
                        "copy": "The wireframe shows the same structure the live error template uses for page recovery.",
                    },
                ),
            ],
        )
    )

    return pages


def build_admin_content_pages() -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []

    pages.append(
        wf_page(
            "admin",
            "shell",
            "Admin Shell",
            "Sidebar navigation, topbar, and protected-control layout.",
            live_endpoint="admin.dashboard",
            sections=[
                wf_section(
                    "shell",
                    "Admin Shell",
                    "Sidebar and topbar composition used by every admin page.",
                    nav_items=ADMIN_NAV_ITEMS,
                    topbar=["Logged-in staff name", "Role label", "Theme toggle", "Logout button"],
                )
            ],
        )
    )

    pages.append(
        wf_page(
            "admin",
            "login",
            "Admin Login",
            "Protected staff access card with CAPTCHA and secure session messaging.",
            live_endpoint="admin.login",
            sections=[
                wf_section(
                    "auth",
                    "Protected Staff Access",
                    "Intro panel plus login card.",
                    intro={
                        "eyebrow": "Protected Staff Access",
                        "title": "AI SOLUTION Control Center",
                        "copy": "Secure enterprise administration with CAPTCHA verification, protected sessions, and activity logging across content, enquiries, client records, media, and performance reporting.",
                        "cards": [
                            {"title": "Private route", "copy": "Secure session controls and noindex headers."},
                            {"title": "Audited sign-ins", "copy": "Monitored logins and activity trails."},
                            {"title": "Content control", "copy": "Manage enquiries, users, and analytics."},
                        ],
                    },
                    panels=[
                        {
                            "title": "Login",
                            "copy": "Email, password, remember device, and CAPTCHA challenge.",
                            "fields": ["Email", "Password", "Remember this device", "Captcha"],
                        }
                    ],
                )
            ],
        )
    )

    pages.append(
        wf_page(
            "admin",
            "dashboard",
            "Dashboard",
            "Metrics, charts, notifications, quick actions, recent lists, and activity feed.",
            live_endpoint="admin.dashboard",
            sections=[
                wf_section(
                    "dashboard",
                    "Operations Overview",
                    "The admin landing page content blocks.",
                    metrics=[
                        {"value": "Inquiries", "label": "Contact submissions"},
                        {"value": "Applications", "label": "Career applications"},
                        {"value": "RSVPs", "label": "Event registrations"},
                        {"value": "Client Accounts", "label": "Public users"},
                        {"value": "Feedback", "label": "Feedback items"},
                        {"value": "Pending Feedback", "label": "Moderation queue"},
                        {"value": "Chatbot Logs", "label": "Assistant logs"},
                        {"value": "Site Visits", "label": "Traffic records"},
                        {"value": "Published Blogs", "label": "Live posts"},
                        {"value": "Failed Logins (24h)", "label": "Security events"},
                    ],
                    charts=[
                        "Monthly Growth",
                        "Service Interest",
                        "Country Analytics",
                    ],
                    lists=[
                        "Notifications",
                        "Quick Actions",
                        "Recent Auth",
                        "Latest Inquiries",
                        "Latest Applications",
                        "Latest Feedback",
                        "Recent Activity",
                    ],
                )
            ],
        )
    )

    table_specs = [
        {
            "slug": "inquiries",
            "title": "Inquiries",
            "summary": "Contact submissions with status changes, export, and delete actions.",
            "live_endpoint": "admin.inquiries",
            "columns": ["full_name", "email", "subject", "company", "country", "service", "status", "created_at"],
            "statuses": ["New", "Contacted", "Qualified", "Closed"],
            "actions": ["Update status", "Export CSV", "Delete"],
        },
        {
            "slug": "applications",
            "title": "Applications",
            "summary": "Career application table with resume download action.",
            "live_endpoint": "admin.applications",
            "columns": ["full_name", "email", "position", "experience", "status", "created_at"],
            "statuses": ["Received", "Screening", "Interview", "Offer", "Rejected"],
            "actions": ["Download resume", "Update status"],
        },
        {
            "slug": "rsvps",
            "title": "RSVPs",
            "summary": "Event registrations with status management.",
            "live_endpoint": "admin.rsvps",
            "columns": ["full_name", "email", "company", "job_title", "preferred_session", "attendees", "status", "created_at"],
            "statuses": ["Confirmed", "Waitlisted", "Cancelled", "Attended"],
            "actions": ["Update status"],
        },
        {
            "slug": "chatbot-logs",
            "title": "Chatbot Logs",
            "summary": "Assistant logs and message activity.",
            "live_endpoint": "admin.chatbot_logs",
            "columns": ["session_id", "intent", "user_message", "bot_response", "created_at"],
            "statuses": [],
            "actions": [],
        },
        {
            "slug": "newsletter",
            "title": "Newsletter Subscribers",
            "summary": "Subscriber table with source and active state.",
            "live_endpoint": "admin.newsletter",
            "columns": ["email", "source", "is_active", "created_at"],
            "statuses": [],
            "actions": [],
        },
        {
            "slug": "clients",
            "title": "Client Users",
            "summary": "Public user accounts with archive and restore actions.",
            "live_endpoint": "admin.client_users",
            "columns": ["full_name", "company", "email", "is_active", "last_login_at", "accepted_privacy"],
            "statuses": [],
            "actions": ["Archive", "Restore", "Delete"],
        },
        {
            "slug": "auth-logs",
            "title": "Authentication Logs",
            "summary": "Admin and public sign-in tracking table.",
            "live_endpoint": "admin.auth_logs",
            "columns": ["user_type", "email", "success", "suspicious", "ip_address", "browser", "device", "operating_system", "failure_reason", "logged_in_at", "logged_out_at"],
            "statuses": [],
            "actions": [],
        },
        {
            "slug": "activity-logs",
            "title": "Activity Logs",
            "summary": "Audit feed for create, update, archive, restore, and delete actions.",
            "live_endpoint": "admin.activity_logs",
            "columns": ["actor_name", "action", "resource_type", "description", "ip_address", "created_at"],
            "statuses": [],
            "actions": [],
        },
        {
            "slug": "feedback",
            "title": "Feedback",
            "summary": "Feedback moderation list with status actions.",
            "live_endpoint": "admin.feedback",
            "columns": ["full_name", "email", "rating", "message", "status", "source_page", "created_at"],
            "statuses": ["Pending", "Approved", "Rejected"],
            "actions": ["Update status", "Delete"],
        },
    ]

    for spec in table_specs:
        pages.append(
            wf_page(
                "admin",
                spec["slug"],
                spec["title"],
                spec["summary"],
                live_endpoint=spec["live_endpoint"],
                sections=[
                    wf_section(
                        "table",
                        spec["title"],
                        "Search, filters, table columns, row actions, and pagination.",
                        columns=spec["columns"],
                        statuses=spec["statuses"],
                        actions=spec["actions"],
                    )
                ],
            )
        )

    for resource, config in CONTENT_RESOURCES.items():
        if resource in {"feedback"}:
            continue
        pages.append(
            wf_page(
                "admin",
                resource,
                config["title"],
                f"{config['title']} content editor with field controls and live list management.",
                live_endpoint="admin.manage_content",
                live_values={"resource": resource},
                sections=[
                    wf_section(
                        "editor",
                        config["title"],
                        "Filter toolbar, create editor, content list, and pagination.",
                        fields=[
                            {"label": label, "type": field_type, "name": name}
                            for name, label, field_type in config["fields"]
                        ],
                        notes=[
                            "Create new records from the editor at the top.",
                            "Each existing record is editable inline.",
                        ],
                        upload_hint=resource in {"media", "site-settings"},
                    )
                ],
            )
        )

    pages.append(
        wf_page(
            "admin",
            "staff",
            "Staff",
            "Create staff accounts and update existing staff records.",
            live_endpoint="admin.staff",
            sections=[
                wf_section(
                    "editor",
                    "Staff Account Management",
                    "Create form plus existing staff list.",
                    fields=[
                        {"label": "Name", "type": "text"},
                        {"label": "Email", "type": "email"},
                        {"label": "Role", "type": "select"},
                        {"label": "Password", "type": "password"},
                        {"label": "Confirm Password", "type": "password"},
                        {"label": "Active", "type": "checkbox"},
                    ],
                    notes=[
                        "Only the Super Admin role can access staff management.",
                        "Existing staff rows can be updated, activated, deactivated, or deleted.",
                    ],
                    records=[
                        {"title": "Existing staff", "copy": "Inline staff record cards with role and active state."},
                    ],
                )
            ],
        )
    )

    return pages


PAGES = build_public_pages() + build_admin_content_pages()
PAGE_LOOKUP = {(page["group"], page["slug"]): page for page in PAGES}


def resolve_page(page: dict[str, Any]) -> dict[str, Any]:
    resolved = deepcopy(page)
    resolved["group_label"] = GROUP_LABELS.get(resolved["group"], resolved["group"].title())
    resolved["section_count"] = len(resolved.get("sections", []))
    if resolved.get("live_endpoint"):
        resolved["live_url"] = url_for(resolved["live_endpoint"], **resolved.get("live_values", {}))
    else:
        resolved["live_url"] = ""
    resolved["wireframe_url"] = url_for("wireframe.page", group=resolved["group"], slug=resolved["slug"])
    for index, section in enumerate(resolved.get("sections", []), start=1):
        section["id"] = f"{slugify(section['label'])}-{index}"
    return resolved


def build_nav_groups(current: tuple[str, str] | None = None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in GROUP_LABELS}
    for page in PAGES:
        grouped.setdefault(page["group"], []).append(page)

    nav_groups = []
    for group, label in GROUP_LABELS.items():
        nav_groups.append(
            {
                "group": group,
                "label": label,
                "pages": [
                    {
                        "title": page["title"],
                        "slug": page["slug"],
                        "summary": page["summary"],
                        "active": current == (page["group"], page["slug"]),
                        "url": url_for("wireframe.page", group=page["group"], slug=page["slug"]),
                    }
                    for page in grouped.get(group, [])
                ],
            }
        )
    return nav_groups


@wireframe_bp.route("/")
def index():
    pages = [resolve_page(page) for page in PAGES]
    return render_template(
        "wireframe/index.html",
        wireframe_title="Website Wireframe",
        wireframe_summary="A faithful HTML blueprint of the live public site and admin panel.",
        pages=pages,
        nav_groups=build_nav_groups(),
        page_count=len(pages),
        public_count=sum(1 for page in pages if page["group"] == "public"),
        client_count=sum(1 for page in pages if page["group"] == "client"),
        admin_count=sum(1 for page in pages if page["group"] == "admin"),
        system_count=sum(1 for page in pages if page["group"] == "system"),
    )


@wireframe_bp.route("/<group>/<slug>")
def page(group: str, slug: str):
    page_data = PAGE_LOOKUP.get((group, slug))
    if not page_data:
        abort(404)
    resolved = resolve_page(page_data)
    return render_template(
        "wireframe/page.html",
        page=resolved,
        nav_groups=build_nav_groups((group, slug)),
        wireframe_title=f"{resolved['title']} Wireframe",
        wireframe_summary=resolved["summary"],
    )
