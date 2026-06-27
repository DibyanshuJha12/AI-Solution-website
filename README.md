
# 🚀 AI-Solutions CMS

<div align="center">

# AI-Solutions CMS

### Intelligent AI-Powered Content Management System

A modern full-stack **Flask** Content Management System that combines a professional corporate website with a secure administration dashboard and an AI-powered chatbot. The application uses **PostgreSQL** as its primary database and **Google Gemini AI** to deliver intelligent conversational assistance.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?style=for-the-badge&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6-F7DF1E?style=for-the-badge&logo=javascript)
![License](https://img.shields.io/badge/License-Academic-success?style=for-the-badge)

</div>

---

# 📖 Overview

AI-Solutions CMS is a professional Content Management System developed as an academic and portfolio project. It provides a responsive public-facing company website together with a secure administration panel that allows administrators to manage website content from a single platform.

The system supports dynamic management of pages, portfolio items, blogs, testimonials, galleries, FAQs, events, team members, user enquiries, roles and site settings. It also integrates Google's Gemini AI to provide intelligent chatbot responses.

---

# ✨ Key Features

## 🌐 Public Website

- Responsive company website
- About, Services and Portfolio pages
- Blog and Articles
- Gallery
- Testimonials
- FAQ section
- Team profiles
- Events
- Contact form
- Cookie consent
- Progressive Web App (PWA) assets
- Gemini AI chatbot

## 🛠️ Admin Dashboard

- Secure administrator login
- Dashboard overview
- Blog management
- Portfolio management
- Gallery management
- Event management
- FAQ management
- Team management
- Testimonial management
- Contact enquiry management
- User and role management
- Site settings
- Activity and audit logs

## 🤖 AI Integration

- Google Gemini API
- Intelligent chatbot responses
- Local fallback behaviour
- Easy API key configuration

---

# 💻 Technology Stack

| Category | Technology |
|----------|------------|
| Backend | Flask 3 |
| Programming Language | Python 3 |
| Database | PostgreSQL |
| Database Driver | pg8000 |
| Authentication | Flask-Login |
| Forms & Validation | Flask-WTF |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Template Engine | Jinja2 |
| AI Integration | Google Gemini API |
| Version Control | Git & GitHub |

---

# 🏗️ System Architecture

```text
Client Browser
      │
      ▼
Flask Application
      │
 ├── Public Website
 ├── Admin Dashboard
 ├── Authentication
 ├── CMS Modules
 ├── Gemini AI Service
 └── Utility Components
      │
      ▼
PostgreSQL Database
```

---

# 📂 Project Structure

```text
AI-Solutions/
│
├── app.py
├── wsgi.py
├── config.py
├── requirements.txt
├── .env.example
│
├── aisolution/
│   ├── routes/
│   ├── services/
│   ├── utilities/
│   ├── templates/
│   └── static/
│
├── migrations/
├── uploads/
└── instance/
```

---

# ⚙️ Installation

```bash
git clone <repository-url>
cd AI-Solutions

python -m venv .venv
```

Activate the virtual environment.

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 🔧 Environment Configuration

Create a `.env` file.

```env
SECRET_KEY=your_secret_key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_solutions_db
DB_USER=postgres
DB_PASSWORD=your_password

ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong_password

GEMINI_API_KEY=your_gemini_api_key
```

> SMTP configuration is intentionally omitted because it is not part of the implemented project.

---

# 🗄️ Database Setup

Create the PostgreSQL database.

```sql
CREATE DATABASE ai_solutions_db;
```

Run the setup commands.

```bash
flask --app app check-db
flask --app app setup
```

---

# ▶️ Running the Application

```bash
flask --app app run
```

Open:

`http://127.0.0.1:5000`

---

# 🔐 Security Features

- Password hashing
- CSRF protection
- Session management
- Role-based authentication
- Parameterized PostgreSQL queries
- Input validation and sanitisation
- Secure environment variable configuration
- Upload validation
- Security headers
- Login history and account protection

---

# ⚡ Useful CLI Commands

```bash
flask --app app check-db
flask --app app setup
flask --app app seed-db
flask --app app routes
```

---

# 🚀 Deployment Checklist

- Configure PostgreSQL
- Set a secure SECRET_KEY
- Configure Gemini API key
- Disable debug mode
- Enable HTTPS
- Configure secure cookies

---

# 🛠️ Troubleshooting

**Database connection issues**

- Verify PostgreSQL is running.
- Check database credentials in `.env`.

**Gemini chatbot unavailable**

- Verify `GEMINI_API_KEY`.

**Unable to login**

- Run:

```bash
flask --app app setup
```

---

# 📈 Future Improvements

- Docker support
- REST API
- Two-factor authentication
- Analytics dashboard
- Multi-language support
- Automated backups

---

# 👨‍💻 Author

**Dibyanshu Jha**

**BSc (Hons) Computer Systems Engineering**

University of Sunderland

Academic Portfolio Project

---

# 📄 License

This project is intended for academic and portfolio purposes. If you plan to publish it publicly, consider adding an open-source license such as MIT or Apache 2.0.
