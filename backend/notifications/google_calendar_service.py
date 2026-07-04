from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime, timedelta
from django.utils import timezone

SCOPES = ["https://www.googleapis.com/auth/calendar"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.pickle")


def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_PATH,
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    service = build("calendar", "v3", credentials=creds)
    return service


def create_calendar_event(appointment):
    service = get_calendar_service()

    slot = appointment.slot

    start_dt = datetime.combine(
        slot.date,
        slot.start_time
    )

    start_dt = timezone.make_aware(start_dt)
    end_dt = start_dt + timedelta(minutes=30)

    doctor_email = slot.doctor.user.email
    patient_email = appointment.patient.user.email

    event = {
        "summary": "Healthcare Appointment",
        "description": f"Appointment ID: {appointment.id}",
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "UTC",
        },
        "attendees": [
            {"email": doctor_email},
            {"email": patient_email},
        ],
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all"
    ).execute()

    return created_event