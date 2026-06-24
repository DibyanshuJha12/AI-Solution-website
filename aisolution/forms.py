from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp, URL


PHONE_RE = r"^[0-9+\-\s()]{7,30}$"
PASSWORD_RE = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$"


class NumericCaptchaMixin:
    captcha_scope = HiddenField("Captcha Scope")
    captcha_answer = StringField("Security Check", validators=[DataRequired(), Length(max=20)])
    recaptcha_token = HiddenField("reCAPTCHA Token")


class InquiryForm(FlaskForm, NumericCaptchaMixin):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    subject = StringField("Subject", validators=[Optional(), Length(max=180)])
    phone = StringField("Phone Number", validators=[Optional(), Regexp(PHONE_RE), Length(max=60)])
    company = StringField("Company Name", validators=[Optional(), Length(max=160)])
    country = StringField("Country", validators=[Optional(), Length(max=100)])
    job_title = StringField("Job Title", validators=[Optional(), Length(max=120)])
    service = SelectField("Service Interested In", choices=[], validators=[DataRequired()])
    contact_method = SelectField(
        "Preferred Contact Method",
        choices=[("Email", "Email"), ("Phone", "Phone"), ("WhatsApp", "WhatsApp"), ("LinkedIn", "LinkedIn")],
        validators=[DataRequired()],
    )
    budget = SelectField(
        "Project Budget",
        choices=[
            ("Under $10k", "Under $10k"),
            ("$10k - $25k", "$10k - $25k"),
            ("$25k - $75k", "$25k - $75k"),
            ("$75k+", "$75k+"),
            ("Not sure yet", "Not sure yet"),
        ],
        validators=[DataRequired()],
    )
    message = TextAreaField("Inquiry Details", validators=[DataRequired(), Length(min=20, max=2000)])
    terms = BooleanField("Terms", validators=[DataRequired()])


class NewsletterForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])


class FeedbackForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=140)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    rating = RadioField(
        "Rating",
        choices=[(1, "1 Star"), (2, "2 Stars"), (3, "3 Stars"), (4, "4 Stars"), (5, "5 Stars")],
        coerce=int,
        default=5,
        validators=[DataRequired()],
    )
    message = TextAreaField("Feedback Message", validators=[DataRequired(), Length(min=20, max=2000)])
    source_page = HiddenField("Source Page")


class ClientLoginForm(FlaskForm, NumericCaptchaMixin):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    remember = BooleanField("Remember this device")


class ClientRegistrationForm(FlaskForm, NumericCaptchaMixin):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    company = StringField("Company Name", validators=[Optional(), Length(max=160)])
    email = EmailField("Business Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=128),
            Regexp(PASSWORD_RE, message="Use uppercase, lowercase, a number, and a symbol."),
        ],
    )
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    remember = BooleanField("Remember this device")
    accept_privacy = BooleanField("Privacy Policy", validators=[DataRequired()])


class ForgotPasswordForm(FlaskForm, NumericCaptchaMixin):
    email = EmailField("Business Email", validators=[DataRequired(), Email(), Length(max=255)])


class ResetPasswordForm(FlaskForm, NumericCaptchaMixin):
    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=8, max=128),
            Regexp(PASSWORD_RE, message="Use uppercase, lowercase, a number, and a symbol."),
        ],
    )
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])


class RSVPForm(FlaskForm, NumericCaptchaMixin):
    event_id = SelectField("Select Event", coerce=int, choices=[], validators=[DataRequired()])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone Number", validators=[DataRequired(), Regexp(PHONE_RE), Length(max=60)])
    company = StringField("Organization", validators=[DataRequired(), Length(max=160)])
    job_title = StringField("Job Title", validators=[DataRequired(), Length(max=120)])
    attendees = IntegerField("Number of Attendees", default=1, validators=[DataRequired(), NumberRange(min=1, max=10)])
    preferred_session = SelectField(
        "Preferred Session",
        choices=[
            ("Executive Briefing", "Executive Briefing"),
            ("Technical Workshop", "Technical Workshop"),
            ("Live Product Demo", "Live Product Demo"),
            ("Strategy Consultation", "Strategy Consultation"),
        ],
        validators=[DataRequired()],
    )
    special_requirements = TextAreaField("Special Requirements", validators=[Optional(), Length(max=800)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=12, max=1500)])
    terms = BooleanField("Terms", validators=[DataRequired()])


class ApplicationForm(FlaskForm, NumericCaptchaMixin):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[DataRequired(), Regexp(PHONE_RE), Length(max=60)])
    address = StringField("Address", validators=[DataRequired(), Length(max=240)])
    position = SelectField("Position Applying For", choices=[], validators=[DataRequired()])
    experience = SelectField(
        "Experience",
        choices=[
            ("0-1 years", "0-1 years"),
            ("2-4 years", "2-4 years"),
            ("5-7 years", "5-7 years"),
            ("8+ years", "8+ years"),
        ],
        validators=[DataRequired()],
    )
    skills = TextAreaField("Skills", validators=[DataRequired(), Length(min=10, max=1200)])
    portfolio_url = StringField("Portfolio URL", validators=[Optional(), URL(), Length(max=500)])
    cover_letter = TextAreaField("Cover Letter", validators=[DataRequired(), Length(min=40, max=3000)])
    resume = FileField(
        "Resume Upload",
        validators=[FileRequired(), FileAllowed(["pdf", "doc", "docx"], "Upload PDF, DOC, or DOCX only.")],
    )
    terms = BooleanField("Terms", validators=[DataRequired()])


class AdminLoginForm(FlaskForm, NumericCaptchaMixin):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    remember = BooleanField("Remember this device")


class StaffForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    role = SelectField(
        "Role",
        choices=[
            ("Super Admin", "Super Admin"),
            ("Admin", "Admin"),
            ("HR Manager", "HR Manager"),
            ("Event Manager", "Event Manager"),
            ("Content Manager", "Content Manager"),
        ],
        validators=[DataRequired()],
    )
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm Password", validators=[Optional(), EqualTo("password")])
    is_active = BooleanField("Active", default=True)
