from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class PatientProfile(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        null=True,
        blank=True
    )

    # ADDED
    emergency_contact = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )

    def clean(self):
        # Edge Case 1:
        # Only patient role allowed
        if self.user.role != "patient":
            raise ValidationError(
                "PatientProfile can only be created for patient users."
            )

        # Edge Case 2:
        # Future DOB invalid
        if self.date_of_birth:
            if self.date_of_birth > timezone.localdate():
                raise ValidationError(
                    "Date of birth cannot be in the future."
                )

        # Edge Case 3:
        # Unrealistic age check (>120 years)
        if self.date_of_birth:
            age = timezone.localdate().year - self.date_of_birth.year

            if age > 120:
                raise ValidationError(
                    "Invalid date of birth."
                )

        # Edge Case 4:
        # Emergency contact should not be same as user phone
        if (
            self.emergency_contact
            and self.user.phone_number == self.emergency_contact
        ):
            raise ValidationError(
                "Emergency contact cannot be same as user's phone number."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.email