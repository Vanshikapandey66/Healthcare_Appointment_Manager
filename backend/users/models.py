from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re


class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("doctor", "Doctor"),
        ("patient", "Patient"),
    )

    email = models.EmailField(
        unique=True
    )

    # ADDED:
    # unique phone so same number multiple accounts me use na ho
    phone_number = models.CharField(
        max_length=15,
        unique=True
    )

    # ADDED:
    # default role patient
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="patient"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username","phone_number","role"]

    def clean(self):
        # phone validation
        if self.phone_number:
            phone_pattern = r'^\+?\d{10,15}$'

            if not re.match(phone_pattern, self.phone_number):
                raise ValidationError(
                    "Enter valid phone number (10-15 digits)."
                )

        # extra safety for role
        valid_roles = [choice[0] for choice in self.ROLE_CHOICES]

        if self.role not in valid_roles:
            raise ValidationError(
                "Invalid user role."
            )

        # admin restrictions
        # normal registration API se admin create nahi hona chahiye
        # if self.role == "admin" and not self.is_staff:
        #     raise ValidationError(
        #         "Admin user must have staff access."
        #     )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} - {self.role}"