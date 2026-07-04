from django.db import models
from doctors.models import DoctorProfile
from patients.models import PatientProfile
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
        unique_together = ("doctor", "date", "start_time", "end_time")

    def clean(self):

        # 1. Past date
        if self.date < timezone.localdate():
            raise ValidationError("Cannot create slot for past dates.")

        # 2. Past time (same day)
        if self.date == timezone.localdate():
            if self.start_time <= timezone.localtime().time():
                raise ValidationError("Cannot create slot in past time.")

        # 3. Time validation
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # 4. Doctor approval
        if self.doctor.approval_status != "approved":
            raise ValidationError("Doctor not approved.")

        # 5. Availability check (FIXED SAFELY)
        weekday = self.date.strftime("%A").lower()

        availability_qs = self.doctor.availabilities.filter(day=weekday)

        if not availability_qs.exists():
            raise ValidationError("Doctor has no availability on this day.")

        valid = False

        for availability in availability_qs:

            if (
                self.start_time >= availability.start_time and
                self.end_time <= availability.end_time
            ):

                slot_minutes = (
                    datetime.combine(self.date, self.end_time) -
                    datetime.combine(self.date, self.start_time)
                ).seconds // 60

                if slot_minutes <= 0:
                    raise ValidationError("Invalid slot duration.")

                if slot_minutes % availability.slot_duration != 0:
                    raise ValidationError("Slot duration mismatch.")

                valid = True
                break

        if not valid:
            raise ValidationError("Slot outside doctor availability.")

        # 6. Leave check
        if self.doctor.leaves.filter(
            leave_date=self.date,
            is_full_day=True
        ).exists():
            raise ValidationError("Doctor on leave.")

        # 7. Partial leave overlap
        partial_leaves = self.doctor.leaves.filter(
            leave_date=self.date,
            is_full_day=False
        )

        for leave in partial_leaves:
            if (
                self.start_time < leave.end_time and
                self.end_time > leave.start_time
            ):
                raise ValidationError("Slot overlaps leave.")

        # 8. Slot overlap
        overlapping = AvailabilitySlot.objects.filter(
            doctor=self.doctor,
            date=self.date
        ).exclude(id=self.id)

        for slot in overlapping:
            if (
                self.start_time < slot.end_time and
                self.end_time > slot.start_time
            ):
                raise ValidationError("Slot overlaps existing slot.")

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

    reason = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )

    reschedule_count = models.PositiveIntegerField(default=0)

    booked_at = models.DateTimeField(auto_now_add=True)

    google_event_id = models.CharField(max_length=255, null=True, blank=True)
    google_meet_link = models.URLField(null=True, blank=True)

    calendar_sync_status = models.CharField(
        max_length=20,
        default="pending"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):

        # 1. Role check
        if self.patient.user.role != "patient":
            raise ValidationError("Only patient can book.")

        # 2. Doctor approval
        if self.slot.doctor.approval_status != "approved":
            raise ValidationError("Doctor not approved.")

        # 3. Past slot check (FIXED)
        slot_dt = datetime.combine(self.slot.date, self.slot.start_time)

        if timezone.is_naive(slot_dt):
            slot_dt = timezone.make_aware(slot_dt)

        if slot_dt < timezone.now():
            raise ValidationError("Cannot book past slot.")

        # 4. Double booking (SAFE)
        existing = Appointment.objects.filter(
            slot=self.slot,
            status="scheduled"
        )

        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError("Slot already booked.")

        # 5. Immutable check
        if self.pk:
            old = Appointment.objects.get(pk=self.pk)
            if old.status in ["completed", "no_show"] and old.status != self.status:
                raise ValidationError("Cannot modify completed/no-show.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        patient_name = (
            self.patient.user.first_name
            or self.patient.user.email
        )
        return f"{patient_name} - {self.slot}"