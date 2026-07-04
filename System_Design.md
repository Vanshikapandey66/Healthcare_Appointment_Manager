# System Design - Healthcare Appointment Manager

## 1. Architecture
This project follows a layered Django architecture:

- Models: Database schema (Patient, Doctor, Appointment, Slots)
- Serializers: Data validation & transformation (DRF)
- Views: Business logic (API endpoints)
- Services: External integrations (Google Calendar, Email, LLM)

---

## 2. Modules

### Users Module
- Handles authentication (JWT)
- Roles: Patient, Doctor, Admin

### Doctor Module
- Doctor registration
- Approval system (admin approval required)
- Availability management

### Appointment Module
- Slot booking
- Rescheduling
- Cancellation
- Status tracking

### Notification Module
- Email notifications
- Appointment updates

### Google Calendar Integration
- Auto event creation on booking
- Meet link generation
- Sync status tracking

### LLM Module
- Appointment suggestions based on symptoms/reason
- Smart scheduling suggestions

---

## 3. Database Design

### Key Tables
- User
- PatientProfile
- DoctorProfile
- AvailabilitySlot
- Appointment
- Notification

---

## 4. Key Workflows

### Appointment Booking Flow
1. Patient selects slot
2. Validation checks (slot availability, doctor approval)
3. Appointment created
4. Google Calendar event created
5. Email notification sent

---

### Slot Creation Flow
1. Doctor creates slot
2. System validates:
   - Availability window
   - Leave conflicts
   - Overlapping slots
3. Slot saved

---

## 5. External Integrations

### Google Calendar API
- OAuth authentication
- Event creation
- Meet link generation

### Email Service
- Django email backend

### LLM Service
- Suggest best appointment time based on request

---

## 6. Security
- JWT authentication
- Role-based access control
- Protected endpoints

---

## 7. Future Improvements
- Frontend React app
- Payment integration
- Advanced AI scheduling