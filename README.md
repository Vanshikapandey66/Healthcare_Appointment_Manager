🏥 Healthcare Appointment & Follow-up Manager

A full-stack backend system for managing healthcare appointments with role-based access (Patient / Doctor / Admin), Google Calendar integration, and LLM-powered medical summaries.

🚀 Features
👤 User Roles
Patient registration & login
Doctor registration (admin approval required)
Admin manages doctors
📅 Appointment System
Book appointments via available slots
Prevent double booking
Reschedule appointments (with rules)
Cancel appointments
Slot availability validation
🧑‍⚕️ Doctor System
Doctor availability slots
Approval system (admin controlled)
Leave handling (model level validation)
🤖 AI (LLM Integration)
Pre-visit Summary
Symptom analysis
Urgency level (Low / Medium / High)
Chief complaint
Suggested doctor questions
Post-visit Summary
Converts doctor notes into patient-friendly summary
Includes medication schedule + follow-up steps
📧 Notifications
Booking confirmation email
Appointment cancellation email
Appointment reschedule email
📆 Google Calendar Integration
Auto event creation on booking
Google Meet link generation
Sync status tracking
Update handling on reschedule/cancel
🏗️ Tech Stack
Python 3.11+
Django 6
Django REST Framework
SQLite / PostgreSQL
OpenAI API (LLM)
Google Calendar API (OAuth2)
📁 Project Structure
backend/
│
├── users/
├── doctors/
├── patients/
├── appointments/
│   ├── views.py
│   ├── models.py
│   ├── serializers.py
│   ├── google_calendar_service.py
│   ├── llm_service.py
│
├── notifications/
├── config/

⚙️ Setup Instructions
1️⃣ Clone Project
git clone <repo-url>
cd backend
2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   # Windows
3️⃣ Install Dependencies
pip install -r requirements.txt
4️⃣ Run Migrations
python manage.py makemigrations
python manage.py migrate
5️⃣ Create Superuser
python manage.py createsuperuser
6️⃣ Run Server
python manage.py runserver
🔑 Environment Variables (.env)
SECRET_KEY=your_secret_key
DEBUG=True

OPENAI_API_KEY=your_openai_key

EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_password
📡 API Endpoints
Auth
POST /api/users/register/
POST /api/users/login/
Doctors
POST /api/doctors/approve/ (admin)
GET /api/doctors/
Slots
POST /api/appointments/slots/
GET /api/appointments/slots/
Appointments
POST /api/appointments/book/
GET /api/appointments/my/
PATCH /api/appointments/reschedule/<id>/
PATCH /api/appointments/status/<id>/
AI (LLM)
POST /api/ai/pre-visit/
POST /api/ai/post-visit/
🤖 LLM Prompts
Pre-Visit
Analyze symptoms:
- urgency level (Low/Medium/High)
- chief complaint
- 3 doctor questions
Post-Visit
Convert clinical notes into:
- patient friendly summary
- medication schedule
- follow-up steps
📆 Google Calendar Setup
Create Google Cloud Project
Enable Google Calendar API
Download credentials.json
Place in backend root
First run generates token.pickle
⚠️ Error Handling Strategy
LLM failures → system continues without breaking
Calendar failures → marked as failed
Email failures → logged + retry possible
Slot conflicts → handled via DB + validation
🧠 System Design Summary (Short)
Uses role-based architecture
Prevents race conditions using DB validation
Ensures single-slot booking integrity
Uses Google Calendar sync for external scheduling
LLM used for:
pre-visit triage
post-visit summarization