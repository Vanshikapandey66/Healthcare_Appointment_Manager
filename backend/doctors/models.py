from django.db import models
from users.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime


class Specialization(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    APPROVAL_STATUS = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile"
    )

    full_name = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    specialization = models.ForeignKey(
        "Specialization",
        on_delete=models.PROTECT,
        related_name="doctors"
    )

    license_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    clinic_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    experience_years = models.PositiveIntegerField()

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default="pending"
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_doctors"
    )

    def clean(self):
        # Edge Case 1: Only doctor user allowed
        if self.user.role != "doctor":
            raise ValidationError(
                "DoctorProfile can only be created for doctor users."
            )

        # Edge Case 2: Fee validation
        if self.consultation_fee <= 0:
            raise ValidationError(
                "Consultation fee must be greater than zero."
            )

        # Edge Case 3: Experience sanity
        if self.experience_years > 80:
            raise ValidationError(
                "Invalid experience years."
            )

        # Edge Case 4: Approved doctor must have license
        if (
            self.approval_status == "approved"
            and not self.license_number
        ):
            raise ValidationError(
                "Approved doctor must have license number."
            )

        # Edge Case 5: Approved doctor must have approver
        if (
            self.approval_status == "approved"
            and not self.approved_by
        ):
            raise ValidationError(
                "Approved doctor must have approved_by."
            )

        # Edge Case 6: Only approved doctor can have approver
        if (
            self.approval_status != "approved"
            and self.approved_by
        ):
            raise ValidationError(
                "Only approved doctors can have approved_by."
            )

        # Edge Case 7: Only admin can approve
        if self.approved_by:
            if self.approved_by.role != "admin":
                raise ValidationError(
                    "Only admin can approve doctors."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        doctor_name = self.full_name or self.user.first_name
        return f"Dr. {doctor_name} ({self.specialization})"


class DoctorAvailability(models.Model):
    DAY_CHOICES = (
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),
    )

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="availabilities"
    )

    day = models.CharField(
        max_length=20,
        choices=DAY_CHOICES
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    slot_duration = models.PositiveIntegerField(
        validators=[
            MinValueValidator(5),
            MaxValueValidator(120)
        ],
        help_text="Duration in minutes"
    )

    def __str__(self):
        doctor_name = (
            self.doctor.full_name
            or self.doctor.user.first_name
        )
        return f"{doctor_name} - {self.day}"

    def clean(self):
        # Start/end validation
        if self.start_time >= self.end_time:
            raise ValidationError(
                "Start time must be earlier than end time."
            )

        # Edge Case 8: Availability duration divisible by slot duration
        total_minutes = (
            datetime.combine(datetime.today(), self.end_time)
            - datetime.combine(datetime.today(), self.start_time)
        ).seconds // 60

        if total_minutes % self.slot_duration != 0:
            raise ValidationError(
                "Availability duration must be divisible by slot duration."
            )

        # Overlap validation
        overlapping_slots = DoctorAvailability.objects.filter(
            doctor=self.doctor,
            day=self.day
        ).exclude(id=self.id)

        for slot in overlapping_slots:
            if (
                self.start_time < slot.end_time
                and self.end_time > slot.start_time
            ):
                raise ValidationError(
                    "This availability overlaps with existing schedule."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DoctorLeave(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="leaves"
    )

    leave_date = models.DateField()

    is_full_day = models.BooleanField(default=True)

    start_time = models.TimeField(
        null=True,
        blank=True
    )

    end_time = models.TimeField(
        null=True,
        blank=True
    )

    reason = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = (
            "doctor",
            "leave_date",
            "start_time",
            "end_time"
        )

    def clean(self):
        if self.is_full_day:
            if self.start_time or self.end_time:
                raise ValidationError(
                    "Full-day leave cannot have start or end time."
                )

            existing_leaves = DoctorLeave.objects.filter(
                doctor=self.doctor,
                leave_date=self.leave_date
            ).exclude(id=self.id)

            if existing_leaves.exists():
                raise ValidationError(
                    "Cannot add full-day leave because leave already exists on this date."
                )

        else:
            if not self.start_time or not self.end_time:
                raise ValidationError(
                    "Partial leave requires start and end time."
                )

            if self.start_time >= self.end_time:
                raise ValidationError(
                    "Leave start time must be before end time."
                )

            # Edge Case 9: Leave must lie inside doctor availability
            weekday = self.leave_date.strftime("%A").lower()

            availabilities = self.doctor.availabilities.filter(
                day=weekday
            )

            valid = False

            for availability in availabilities:
                if (
                    self.start_time >= availability.start_time
                    and self.end_time <= availability.end_time
                ):
                    valid = True
                    break

            if not valid:
                raise ValidationError(
                    "Leave timing must be inside doctor availability."
                )

            full_day_leave_exists = DoctorLeave.objects.filter(
                doctor=self.doctor,
                leave_date=self.leave_date,
                is_full_day=True
            ).exclude(id=self.id).exists()

            if full_day_leave_exists:
                raise ValidationError(
                    "Doctor already has full-day leave on this date."
                )

            overlapping_leaves = DoctorLeave.objects.filter(
                doctor=self.doctor,
                leave_date=self.leave_date,
                is_full_day=False
            ).exclude(id=self.id)

            for leave in overlapping_leaves:
                if (
                    self.start_time < leave.end_time
                    and self.end_time > leave.start_time
                ):
                    raise ValidationError(
                        "This leave overlaps with an existing leave."
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        doctor_name = (
            self.doctor.full_name
            or self.doctor.user.first_name
        )

        if self.is_full_day:
            return f"{doctor_name} - {self.leave_date} (Full Day)"

        return (
            f"{doctor_name} - {self.leave_date} "
            f"({self.start_time} - {self.end_time})"
        )