import os
import pickle
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None

    token_path = os.path.join(settings.BASE_DIR, "token.pickle")
    credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")

    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    elif not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)


def create_calendar_event(appointment):
    # already synced → skip
    if appointment.google_event_id:
        return

    service = get_calendar_service()

    start_dt = timezone.make_aware(
        datetime.combine(
            appointment.slot.date,
            appointment.slot.start_time
        )
    )

    end_dt = timezone.make_aware(
        datetime.combine(
            appointment.slot.date,
            appointment.slot.end_time
        )
    )

    patient_email = appointment.patient.user.email
    doctor_email = appointment.slot.doctor.user.email

    if not patient_email or not doctor_email:
        raise Exception("Doctor or patient email missing")

    event = {
        "summary": "Healthcare Appointment",
        "description": appointment.reason or "Appointment",
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "attendees": [
            {"email": patient_email},
            {"email": doctor_email},
        ],
        "conferenceData": {
            "createRequest": {
                "requestId": f"appt-{appointment.id}"
            }
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all"
    ).execute()

    appointment.google_event_id = created_event["id"]
    appointment.google_meet_link = created_event.get("hangoutLink")
    appointment.calendar_sync_status = "synced"
    appointment.save()