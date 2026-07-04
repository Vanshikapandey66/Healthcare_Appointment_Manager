from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from doctors.models import DoctorProfile
from django.utils import timezone
from datetime import datetime,timedelta
from django.db import transaction
from notifications.models import Notification
from notifications.services import send_notification_email
from .models import AvailabilitySlot, Appointment
from .llm_service import pre_visit_summary, post_visit_summary
from .google_calendar_service import (
    create_calendar_event
)
from .serializers import (
    AvailabilitySlotSerializer,
    AppointmentCreateSerializer,
    AppointmentListSerializer,
    AppointmentStatusSerializer,
    AppointmentRescheduleSerializer
)


class SlotListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        slots = AvailabilitySlot.objects.all()

        doctor_id = request.query_params.get("doctor")
        date = request.query_params.get("date")

        if doctor_id:
            slots = slots.filter(doctor_id=doctor_id)

        if date:
            slots = slots.filter(date=date)

        valid_slots = []

        for slot in slots:
            slot_datetime = datetime.combine(
                slot.date,
                slot.start_time
            )
            print("NOW:", timezone.now())
            print("SLOT:", slot.date, slot.start_time)
            print("COMBINED:", slot_datetime)

            if timezone.is_naive(slot_datetime):
                slot_datetime = timezone.make_aware(
                    slot_datetime
                )

            # EC14: hide past slots
            if slot_datetime <= timezone.now():
                continue

            # hide already booked slots
            if slot.appointments.filter(
                status="scheduled"
            ).exists():
                continue

            valid_slots.append(slot)

        serializer = AvailabilitySlotSerializer(
            valid_slots,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):
        # EC10
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors can create slots."},
                status=status.HTTP_403_FORBIDDEN
            )

        # EC16
        if (
            request.user.doctor_profile.approval_status
            != "approved"
        ):
            return Response(
                {
                    "error":
                    "Unapproved doctors cannot create slots."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AvailabilitySlotSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class MySlotsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        slots = AvailabilitySlot.objects.filter(
            doctor=request.user.doctor_profile
        )

        serializer = AvailabilitySlotSerializer(
            slots,
            many=True
        )

        return Response(serializer.data)


class SlotDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, slot_id):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            slot = AvailabilitySlot.objects.get(id=slot_id)
        except AvailabilitySlot.DoesNotExist:
            return Response(
                {"error": "Slot not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # EC11
        if slot.doctor != request.user.doctor_profile:
            return Response(
                {"error": "Not your slot."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AvailabilitySlotSerializer(
            slot,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, slot_id):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            slot = AvailabilitySlot.objects.get(id=slot_id)
        except AvailabilitySlot.DoesNotExist:
            return Response(
                {"error": "Slot not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if slot.doctor != request.user.doctor_profile:
            return Response(
                {"error": "Not your slot."},
                status=status.HTTP_403_FORBIDDEN
            )

        # EC12
        if slot.appointments.filter(
            status="scheduled"
        ).exists():
            return Response(
                {
                    "error":
                    "Booked slot cannot be deleted."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        slot.delete()

        return Response(
            {"message": "Slot deleted successfully."}
        )


class AppointmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients can book appointments."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AppointmentCreateSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment = None

        try:
            with transaction.atomic():

                # 1. CREATE APPOINTMENT
                appointment = serializer.save()

                # 2. 🔥 LLM PRE-VISIT INTEGRATION (FIX ADDED)
                try:
                    symptoms = appointment.reason or ""
                    llm_result = pre_visit_summary(symptoms)

                    # safe attach (DON'T crash if field missing)
                    if hasattr(appointment, "llm_summary"):
                        appointment.llm_summary = llm_result
                        appointment.save()

                except Exception:
                    pass  # NEVER break booking flow

                # 3. GOOGLE CALENDAR (SAFE FIXED)
                try:
                    create_calendar_event(appointment)
                    appointment.calendar_sync_status = "synced"
                except Exception:
                    appointment.calendar_sync_status = "failed"

                appointment.save()

        except Exception:
            return Response(
                {"error": "Appointment booking failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4. NOTIFICATION (UNCHANGED BUT SAFE)
        try:
            notification = Notification.objects.create(
                recipient=request.user,
                appointment=appointment,
                notification_type="booking_confirmation",
                subject="Appointment Booked Successfully",
                message=(
                    f"Your appointment has been booked for "
                    f"{appointment.slot.date} at "
                    f"{appointment.slot.start_time}."
                )
            )

            send_notification_email(notification)

        except Exception:
            pass

        return Response(
            AppointmentListSerializer(appointment).data,
            status=status.HTTP_201_CREATED
        )


# ---------------- POST VISIT LLM (FIXED SAFE) ----------------

class PostVisitLLMView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        notes = request.data.get("notes", "")

        try:
            result = post_visit_summary(notes)
        except Exception:
            result = "Summary not available"

        return Response({"summary": result})


# ---------------- PRE VISIT (SAFE) ----------------

class PreVisitLLMView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        symptoms = request.data.get("symptoms", "")

        try:
            result = pre_visit_summary(symptoms)
        except Exception:
            result = "Unable to generate summary"

        return Response({"summary": result})


class MyAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        appointments = Appointment.objects.filter(
            patient=request.user.patient_profile
        )

        serializer = AppointmentListSerializer(
            appointments,
            many=True
        )

        return Response(serializer.data)


class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(
                id=appointment_id
            )
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # EC23 EC24 EC25
        if request.user.role == "patient":
            if appointment.patient != request.user.patient_profile:
                return Response(
                    {"error": "Unauthorized."},
                    status=status.HTTP_403_FORBIDDEN
                )

        elif request.user.role == "doctor":
            if (
                appointment.slot.doctor
                != request.user.doctor_profile
            ):
                return Response(
                    {"error": "Unauthorized."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = AppointmentListSerializer(
            appointment
        )
        return Response(serializer.data)


class AppointmentStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(
                id=appointment_id
            )
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get("status")

        if new_status == "cancelled":
            if request.user.role != "patient":
                return Response(
                    {"error": "Only patient can cancel."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if appointment.patient != request.user.patient_profile:
                return Response(
                    {"error": "Unauthorized."},
                    status=status.HTTP_403_FORBIDDEN
                )

        elif new_status in ["completed", "no_show"]:
            if request.user.role != "doctor":
                return Response(
                    {"error": "Only doctors allowed."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # EC22
            if (
                appointment.slot.doctor
                != request.user.doctor_profile
            ):
                return Response(
                    {"error": "Unauthorized."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = AppointmentStatusSerializer(
            appointment,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            updated_appointment = serializer.save()
            if updated_appointment.status == "cancelled":
                updated_appointment.calendar_sync_status = "cancelled"
                updated_appointment.save()

            if updated_appointment.status == "cancelled":
                notification = Notification.objects.create(
                    recipient=updated_appointment.patient.user,
                    appointment=updated_appointment,
                    notification_type="appointment_cancelled",
                    subject="Appointment Cancelled",
                    message=(
                        f"Your appointment scheduled on "
                        f"{updated_appointment.slot.date} at "
                        f"{updated_appointment.slot.start_time} "
                        f"has been cancelled."
                    )
                )

                send_notification_email(notification)

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class DoctorAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        appointments = Appointment.objects.filter(
            slot__doctor=request.user.doctor_profile
        )

        serializer = AppointmentListSerializer(
            appointments,
            many=True
        )

        return Response(serializer.data)


class AllAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            return Response(
                {"error": "Only admin allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        appointments = Appointment.objects.all()

        serializer = AppointmentListSerializer(
            appointments,
            many=True
        )

        return Response(serializer.data)
    
class AppointmentRescheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():
                appointment = (
                    Appointment.objects
                    .select_for_update()
                    .get(id=appointment_id)
                )
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if appointment.patient != request.user.patient_profile:
            return Response(
                {"error": "Unauthorized."},
                status=status.HTTP_403_FORBIDDEN
            )

        if appointment.status != "scheduled":
            return Response(
                {
                    "error":
                    "Only scheduled appointments can be rescheduled."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        current_datetime = datetime.combine(
            appointment.slot.date,
            appointment.slot.start_time
        )

        if timezone.is_naive(current_datetime):
            current_datetime = timezone.make_aware(
                current_datetime
            )

        if current_datetime <= timezone.now():
            return Response(
                {"error": "Past appointment cannot be rescheduled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cutoff_time = current_datetime - timedelta(hours=2)

        if timezone.now() >= cutoff_time:
            return Response(
                {
                    "error":
                    "Reschedule allowed only 2 hours before appointment."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if appointment.reschedule_count >= 3:
            return Response(
                {"error": "Maximum reschedule limit reached."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AppointmentRescheduleSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        new_slot = serializer.validated_data["slot"]
        new_slot_datetime = datetime.combine(
            new_slot.date,
            new_slot.start_time
        )

        if timezone.is_naive(new_slot_datetime):
            new_slot_datetime = timezone.make_aware(
                new_slot_datetime
            )

        if new_slot_datetime <= timezone.now():
            return Response(
                {"error": "Cannot reschedule to past slot."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_slot.id == appointment.slot.id:
            return Response(
                {"error": "Same slot selected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_slot.doctor != appointment.slot.doctor:
            return Response(
                {"error": "Cannot change doctor while rescheduling."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            locked_slot = (
                AvailabilitySlot.objects
                .select_for_update()
                .get(id=new_slot.id)
            )

            if locked_slot.appointments.filter(
                status="scheduled"
            ).exists():
                return Response(
                    {"error": "Slot already booked."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        appointment.slot = locked_slot
        appointment.reschedule_count += 1
        appointment.save()
        if appointment.google_event_id:
            appointment.google_event_id = None
            appointment.google_meet_link = None
            appointment.calendar_sync_status = "pending"
            appointment.save()

            try:
                create_calendar_event(appointment)
            except Exception:
                appointment.calendar_sync_status = "failed"
                appointment.save()
        notification = Notification.objects.create(
            recipient=appointment.patient.user,
            appointment=appointment,
            notification_type="booking_confirmation",
            subject="Appointment Rescheduled",
            message=(
                f"Your appointment has been rescheduled to "
                f"{appointment.slot.date} at "
                f"{appointment.slot.start_time}."
            )
        )

        send_notification_email(notification)

        return Response(
            AppointmentListSerializer(
                appointment
            ).data
        )
    
class PreVisitLLMView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        symptoms = request.data.get("symptoms", "")
        result = pre_visit_summary(symptoms)

        return Response({"summary": result})


class PostVisitLLMView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notes = request.data.get("notes", "")
        result = post_visit_summary(notes)

        return Response({"summary": result})