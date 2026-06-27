



# 🚀 AI-Solutions CMS

<div align="center">

### **AI-Powered Content Management System for Modern Business Websites**

A professional full-stack **Flask** Content Management System featuring a responsive corporate website, secure administration dashboard, AI-powered chatbot, PostgreSQL database integration, and comprehensive content management capabilities.

![Python](https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?style=for-the-badge&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red?style=for-the-badge)
![Jinja2](https://img.shields.io/badge/Jinja2-Templates-B41717?style=for-the-badge)
![License](https://img.shields.io/badge/License-Academic-success?style=for-the-badge)

</div>

---

# 📖 Table of Contents

- Overview
- Key Features
- Technology Stack
- System Architecture
- Project Structure
- Installation
- Configuration
- Database Setup
- Running the Project
- AI Chatbot
- Admin Dashboard
- Public Website
- Security
- CLI Commands
- Deployment
- Troubleshooting
- Future Improvements
- Author
- License

---

# 🌟 Overview

**AI-Solutions CMS** is a modern Content Management System developed using **Python Flask** and **PostgreSQL**. The application combines a responsive corporate website with a powerful administration dashboard, enabling administrators to manage dynamic website content from a single platform.

The system includes content management for blogs, portfolio items, testimonials, gallery images, FAQs, team members, pages, inquiries, users, roles, and website settings. It also integrates an AI-powered chatbot using Google's Gemini API to provide intelligent responses for visitors.

---

# ✨ Key Features

## 🌐 Public Website

- Responsive landing page
- Company information
- AI solutions showcase
- Portfolio & case studies
- Blog & articles
- Team members
- Gallery
- Testimonials
- FAQs
- Events
- Contact form
- Cookie consent
- Progressive Web App (PWA) assets
- Gemini AI chatbot integration

## 🛠️ Administration Dashboard

- Secure administrator authentication
- Dashboard overview
- Content management
- Blog management
- Portfolio management
- Gallery management
- Event management
- FAQ management
- Team management
- Testimonial management
- Contact inquiry management
- User & role management
- Audit & activity logs
- Site configuration

## 🤖 AI Assistant

- Google Gemini API integration
- Context-aware responses
- Local fallback behaviour
- Easily configurable API key

---

# 💻 Technology Stack

| Category | Technology |
|----------|------------|
| Backend | Flask 3 |
| Language | Python 3 |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Forms | Flask-WTF |
| Authentication | Flask-Login |
| Database Migration | Flask-Migrate |
| Templates | Jinja2 |
| Frontend | HTML5, CSS3, JavaScript |
| AI | Google Gemini API |

---

# 🏗️ System Architecture

```text
Browser
    │
    ▼
Flask Application
    │
 ├── Public Website
 ├── Authentication
 ├── Admin Dashboard
 ├── CMS Services
 ├── Gemini AI Service
 └── Utility Modules
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
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── utilities/
│   ├── templates/
│   └── static/
│
├── migrations/
├── instance/
└── uploads/
```

---

# ⚙️ Installation

```bash
git clone <repository-url>
cd AI-Solutions
python -m venv .venv
```

Activate the virtual environment.

**Windows**

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies.

```bash
pip install -r requirements.txt
```

---

# 🔧 Configuration

Create your `.env` file.

```env
SECRET_KEY=your-secret-key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_solutions_db
DB_USER=postgres
DB_PASSWORD=your_password

ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong_password

GEMINI_API_KEY=your_api_key
```

> **Note:** SMTP/email configuration is intentionally omitted because it is not part of the implemented project.

---

# 🗄️ Database Setup

```sql
CREATE DATABASE ai_solutions_db;
```

Initialize the project.

```bash
flask --app app check-db
flask --app app setup
```

---

# ▶️ Running the Project

```bash
flask --app app run
```

Open:

```
http://127.0.0.1:5000
```

---

# 🤖 AI Chatbot

The application supports Google Gemini AI for intelligent conversations.

Features include:

- AI-powered responses
- Configurable API key
- Local fallback behaviour
- Flask service integration

---

# 🔐 Security

- Password hashing
- CSRF protection
- Session management
- Role-based authorization
- SQLAlchemy ORM protection
- Secure environment variables
- File upload validation
- Login history
- Security headers

---

# ⚡ CLI Commands

```bash
flask --app app check-db
flask --app app setup
flask --app app seed-db
flask --app app routes
flask --app app db migrate
flask --app app db upgrade
```

---

# 🚀 Deployment Checklist

- Configure production PostgreSQL
- Generate secure SECRET_KEY
- Disable debug mode
- Configure Gemini API key
- Enable HTTPS
- Configure secure cookies

---

# 🛠️ Troubleshooting

### Database connection failed

Verify PostgreSQL is running and check `.env` values.

### AI chatbot unavailable

Verify the Gemini API key.

### Administrator account missing

Run:

```bash
flask --app app setup
```

---

# 📈 Future Improvements

- Docker support
- REST API
- Dark mode
- Analytics dashboard
- Two-factor authentication
- Multi-language support
- Automated backups

---

# 👨‍💻 Author

**Dibyanshu Jha**

**BSc (Hons) Computer Systems Engineering**

University of Sunderland

Academic Portfolio Project (AI Solution)

---

# 📄 License

This project has been developed for academic and portfolio purposes. If you intend to publish or reuse this project publicly, consider adding an appropriate open-source license such as MIT or Apache 2.0.
