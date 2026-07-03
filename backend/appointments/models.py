from django.db import models
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime


class AvailabilitySlot(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="slots"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = (
            "doctor",
            "date",
            "start_time",
            "end_time"
        )

    def clean(self):

        # Edge Case 1: Past slot creation
        if self.date < timezone.localdate():
            raise ValidationError(
                "Cannot create slot for past dates."
            )

        # Edge Case 2: Same-day past time slot creation
        if self.date == timezone.localdate():
            current_time = timezone.localtime().time()

            if self.start_time <= current_time:
                raise ValidationError(
                    "Cannot create slot in past time."
                )

        # Edge Case 3: Invalid timing
        if self.start_time >= self.end_time:
            raise ValidationError(
                "Start time must be before end time."
            )

        # Edge Case 4: Doctor approval check
        if self.doctor.approval_status != "approved":
            raise ValidationError(
                "Cannot create slots for unapproved doctor."
            )

        weekday = self.date.strftime("%A").lower()

        availability_qs = self.doctor.availabilities.filter(
            day=weekday
        )

        valid = False

        for availability in availability_qs:
            if (
                self.start_time >= availability.start_time
                and self.end_time <= availability.end_time
            ):
                # Edge Case 5: Slot duration check
                slot_minutes = (
                    datetime.combine(self.date, self.end_time)
                    - datetime.combine(self.date, self.start_time)
                ).seconds // 60

                if slot_minutes != availability.slot_duration:
                    raise ValidationError(
                        "Slot duration does not match doctor's slot duration."
                    )

                # Edge Case 6: Slot alignment check
                availability_start = datetime.combine(
                    self.date,
                    availability.start_time
                )

                slot_start = datetime.combine(
                    self.date,
                    self.start_time
                )

                minutes_from_start = (
                    slot_start - availability_start
                ).seconds // 60

                if (
                    minutes_from_start
                    % availability.slot_duration != 0
                ):
                    raise ValidationError(
                        "Slot start time does not align with doctor slot duration."
                    )

                valid = True
                break

        if not valid:
            raise ValidationError(
                "Slot is outside doctor availability."
            )

        # Edge Case 7: Full-day leave
        full_day_leave = self.doctor.leaves.filter(
            leave_date=self.date,
            is_full_day=True
        ).exists()

        if full_day_leave:
            raise ValidationError(
                "Doctor is on full-day leave."
            )

        # Edge Case 8: Partial leave overlap
        partial_leaves = self.doctor.leaves.filter(
            leave_date=self.date,
            is_full_day=False
        )

        for leave in partial_leaves:
            if (
                self.start_time < leave.end_time
                and self.end_time > leave.start_time
            ):
                raise ValidationError(
                    "Slot overlaps with doctor leave."
                )

        # Edge Case 9: Slot overlap with existing slot
        overlapping_slots = AvailabilitySlot.objects.filter(
            doctor=self.doctor,
            date=self.date
        ).exclude(id=self.id)

        for slot in overlapping_slots:
            if (
                self.start_time < slot.end_time
                and self.end_time > slot.start_time
            ):
                raise ValidationError(
                    "Slot overlaps with existing slot."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        doctor_name = (
            self.doctor.full_name
            or self.doctor.user.first_name
        )
        return (
            f"{doctor_name} - "
            f"{self.date} "
            f"{self.start_time}-{self.end_time}"
        )


class Appointment(models.Model):
    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    )

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    reason = models.TextField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )

    booked_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):

        # Edge Case 10: Patient role validation
        if self.patient.user.role != "patient":
            raise ValidationError(
                "Appointment can only be booked by patient."
            )

        # Edge Case 11: Doctor approval check
        if self.slot.doctor.approval_status != "approved":
            raise ValidationError(
                "Cannot book appointment with unapproved doctor."
            )

        # Edge Case 12: Past slot booking (date + time)
        slot_datetime = datetime.combine(
            self.slot.date,
            self.slot.start_time
        )

        if timezone.is_naive(slot_datetime):
            slot_datetime = timezone.make_aware(
                slot_datetime
            )

        if slot_datetime < timezone.now():
            raise ValidationError(
                "Cannot book past slot."
            )

        # Edge Case 13: Double booking
        existing = Appointment.objects.filter(
            slot=self.slot,
            status="scheduled"
        )

        if self.pk:
            existing = existing.exclude(
                pk=self.pk
            )

        if existing.exists():
            raise ValidationError(
                "Slot already booked."
            )

        # Edge Case 14: Completed / no-show immutable
        if self.pk:
            old = Appointment.objects.get(pk=self.pk)

            if old.status in ["completed", "no_show"]:
                if old.status != self.status:
                    raise ValidationError(
                        "Completed or no-show appointments cannot be modified."
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        patient_name = (
            self.patient.user.first_name
            or self.patient.user.email
        )
        return f"{patient_name} - {self.slot}"