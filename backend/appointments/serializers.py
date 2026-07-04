from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from doctors.models import DoctorLeave
from .models import AvailabilitySlot, Appointment
from patients.models import PatientProfile

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = [
            "id",
            "doctor",
            "date",
            "start_time",
            "end_time"
        ]
        read_only_fields = ["doctor"]

    def validate(self, attrs):
        request = self.context.get("request")
        doctor = request.user.doctor_profile

        instance = getattr(self, "instance", None)

        date = attrs.get(
            "date",
            instance.date if instance else None
        )

        start_time = attrs.get(
            "start_time",
            instance.start_time if instance else None
        )

        # Edge Case 12:
        # booked slot update forbidden
        if instance:
            if instance.appointments.filter(
                status="scheduled"
            ).exists():
                raise serializers.ValidationError(
                    "Booked slot cannot be modified."
                )

        # Edge Case 14:
        # past slots hidden / invalid for update
        if date:
            if date < timezone.localdate():
                raise serializers.ValidationError(
                    "Past slot not allowed."
                )

            if date == timezone.localdate():
                current_time = timezone.localtime().time()

                if start_time and start_time <= current_time:
                    raise serializers.ValidationError(
                        "Past time slot not allowed."
                    )

        attrs["doctor"] = doctor
        return attrs

    def create(self, validated_data):
        return AvailabilitySlot.objects.create(
            **validated_data
        )

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()
        return instance


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            "id",
            "slot",
            "reason"
        ]

    def validate_slot(self, slot):
        # Edge Case 21
        if not slot:
            raise serializers.ValidationError(
                "Invalid slot."
            )

        # Edge Case 14
        slot_datetime = datetime.combine(
            slot.date,
            slot.start_time
        )

        if timezone.is_naive(slot_datetime):
            slot_datetime = timezone.make_aware(
                slot_datetime
            )

        if slot_datetime < timezone.now():
            raise serializers.ValidationError(
                "Cannot book past slot."
            )
        
        if slot.appointments.filter(
            status="scheduled"
        ).exists():
            raise serializers.ValidationError(
                "Slot already booked."
            )

        return slot

    def validate(self, attrs):
        request = self.context.get("request")
        print("USER ID:", request.user.id)
        print("EMAIL:", request.user.email)
        print("ROLE:", request.user.role)

        from patients.models import PatientProfile
        print(
            "PROFILE EXISTS:",
            PatientProfile.objects.filter(
                user=request.user
            ).exists()
        )
        patient = PatientProfile.objects.get(user=request.user)
        slot = attrs.get("slot")

        # Edge Case 20
        existing = Appointment.objects.filter(
            patient=patient,
            slot=slot,
            status="scheduled"
        )

        if existing.exists():
            raise serializers.ValidationError(
                "Duplicate appointment request."
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        appointment = Appointment.objects.create(
            patient=PatientProfile.objects.get(user=request.user),   
            **validated_data
        )

        return appointment


class AppointmentListSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    slot_date = serializers.SerializerMethodField()
    slot_start_time = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient_email",
            "doctor_name",
            "slot_date",
            "slot_start_time",
            "reason",
            "status",
            "booked_at"
        ]

    def get_patient_email(self, obj):
        return obj.patient.user.email

    def get_doctor_name(self, obj):
        doctor = obj.slot.doctor
        return (
            doctor.full_name
            or doctor.user.email
        )

    def get_slot_date(self, obj):
        return obj.slot.date

    def get_slot_start_time(self, obj):
        return obj.slot.start_time


class AppointmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["status"]

    def validate_status(self, value):
        valid_status = [
            "cancelled",
            "completed",
            "no_show"
        ]

        if value not in valid_status:
            raise serializers.ValidationError(
                "Invalid status update."
            )

        return value
    
class AppointmentRescheduleSerializer(
    serializers.Serializer
):
    slot = serializers.IntegerField()

    def validate_slot(self, value):
        try:
            slot = AvailabilitySlot.objects.get(id=value)
        except AvailabilitySlot.DoesNotExist:
            raise serializers.ValidationError(
                "Slot not found."
            )

        slot_datetime = datetime.combine(
            slot.date,
            slot.start_time
        )

        if timezone.is_naive(slot_datetime):
            slot_datetime = timezone.make_aware(
                slot_datetime
            )

        if slot_datetime <= timezone.now():
            raise serializers.ValidationError(
                "Past slot cannot be selected."
            )

        if slot.appointments.filter(
            status="scheduled"
        ).exists():
            raise serializers.ValidationError(
                "Slot already booked."
            )

        leave_qs = DoctorLeave.objects.filter(
            doctor=slot.doctor,
            leave_date=slot.date
        )

        for leave in leave_qs:
            if leave.is_full_day:
                raise serializers.ValidationError(
                    "Doctor unavailable on selected date."
                )

            if (
                leave.start_time
                and leave.end_time
                and slot.start_time < leave.end_time
                and slot.end_time > leave.start_time
            ):
                raise serializers.ValidationError(
                    "Doctor unavailable during slot."
                )

        return slot

    def validate(self, attrs):
        instance = self.instance
        new_status = attrs.get("status")

        slot_datetime = datetime.combine(
            instance.slot.date,
            instance.slot.start_time
        )

        if timezone.is_naive(slot_datetime):
            slot_datetime = timezone.make_aware(
                slot_datetime
            )

        
        if instance.status == "cancelled":
            raise serializers.ValidationError(
                "Cancelled appointment cannot be modified."
            )

        
        if instance.status == "completed":
            raise serializers.ValidationError(
                "Completed appointment immutable."
            )

        
        if instance.status == "no_show":
            raise serializers.ValidationError(
                "No-show appointment immutable."
            )

       
        if (
            new_status == "cancelled"
            and slot_datetime <= timezone.now()
        ):
            raise serializers.ValidationError(
                "Past appointment cannot be cancelled."
            )

        
        if (
            new_status == "completed"
            and slot_datetime > timezone.now()
        ):
            raise serializers.ValidationError(
                "Future appointment cannot be completed."
            )

        
        if (
            new_status == "no_show"
            and slot_datetime > timezone.now()
        ):
            raise serializers.ValidationError(
                "Future appointment cannot be marked no-show."
            )

        return attrs