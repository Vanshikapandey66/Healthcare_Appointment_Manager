from django.db import models
from django.core.exceptions import ValidationError
from patients.models import PatientProfile
from appointments.models import Appointment
from doctors.models import Specialization


class AIInteraction(models.Model):
    INTERACTION_CHOICES = (
        ("pre_visit", "Pre Visit"),
        ("post_visit", "Post Visit"),
        ("follow_up", "Follow Up"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    URGENCY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("emergency", "Emergency"),
    )

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="ai_interactions"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_interactions"
    )

    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_CHOICES
    )

    input_text = models.TextField()

    symptoms = models.TextField(
        null=True,
        blank=True
    )

    output_text = models.TextField(
        null=True,
        blank=True
    )

    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        null=True,
        blank=True
    )

    recommended_specialization = models.ForeignKey(
        Specialization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_recommendations"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    model_name = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    tokens_used = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    retry_count = models.PositiveIntegerField(
        default=0
    )

    error_message = models.TextField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):

        # Edge Case 1: Empty input
        if not self.input_text.strip():
            raise ValidationError(
                "Input text cannot be empty."
            )

        # Edge Case 2: Very large prompt
        if len(self.input_text) > 5000:
            raise ValidationError(
                "Input text exceeds maximum allowed length."
            )

        # Edge Case 3:
        # Post visit must have appointment
        if (
            self.interaction_type == "post_visit"
            and not self.appointment
        ):
            raise ValidationError(
                "Post-visit interaction requires appointment."
            )

        # Edge Case 4:
        # Wrong patient-appointment mapping
        if (
            self.appointment
            and self.appointment.patient != self.patient
        ):
            raise ValidationError(
                "Appointment does not belong to this patient."
            )

        # Edge Case 5:
        # Completed but no output
        if (
            self.status == "completed"
            and not self.output_text
        ):
            raise ValidationError(
                "Completed interaction must have output."
            )

        # Edge Case 6:
        # Pending but output exists
        if (
            self.status == "pending"
            and self.output_text
        ):
            raise ValidationError(
                "Pending interaction cannot have output."
            )

        # Edge Case 7:
        # Failed but no error
        if (
            self.status == "failed"
            and not self.error_message
        ):
            raise ValidationError(
                "Failed interaction must store error message."
            )

        # Edge Case 8:
        # Retry overflow
        if self.retry_count > 3:
            raise ValidationError(
                "Retry count cannot exceed 3."
            )

        # Edge Case 9:
        # Pending with token count
        if (
            self.status == "pending"
            and self.tokens_used
        ):
            raise ValidationError(
                "Pending interaction cannot have token usage."
            )

        # Edge Case 10:
        # Completed must have model name
        if (
            self.status == "completed"
            and not self.model_name
        ):
            raise ValidationError(
                "Completed interaction must store model name."
            )

        # Edge Case 11:
        # Completed must have completed_at
        if (
            self.status == "completed"
            and not self.completed_at
        ):
            raise ValidationError(
                "Completed interaction must have completion time."
            )

        # Edge Case 12:
        # Pending cannot have completed_at
        if (
            self.status == "pending"
            and self.completed_at
        ):
            raise ValidationError(
                "Pending interaction cannot have completion time."
            )

        # Edge Case 13:
        # Failed cannot have output
        if (
            self.status == "failed"
            and self.output_text
        ):
            raise ValidationError(
                "Failed interaction cannot have output."
            )

        # Edge Case 14:
        # completed_at before creation
        if (
            self.completed_at
            and self.created_at
            and self.completed_at < self.created_at
        ):
            raise ValidationError(
                "Completion time cannot be before creation time."
            )

        # Edge Case 15:
        # Duplicate active requests
        active_requests = AIInteraction.objects.filter(
            patient=self.patient,
            interaction_type=self.interaction_type,
            status="pending"
        ).exclude(id=self.id)

        if active_requests.exists():
            raise ValidationError(
                "Another pending AI request already exists."
            )

        # Edge Case 16:
        # Symptoms too large
        if self.symptoms and len(self.symptoms) > 1000:
            raise ValidationError(
                "Symptoms field too large."
            )

        # Edge Case 17:
        # Emergency should recommend specialization
        if (
            self.urgency_level == "emergency"
            and not self.recommended_specialization
        ):
            raise ValidationError(
                "Emergency cases should recommend specialization."
            )

        # Edge Case 18:
        # Completed should not have error
        if (
            self.status == "completed"
            and self.error_message
        ):
            raise ValidationError(
                "Completed interaction cannot have error message."
            )

        # Edge Case 19:
        # Failed should not have completion time
        if (
            self.status == "failed"
            and self.completed_at
        ):
            raise ValidationError(
                "Failed interaction cannot have completion time."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        patient_name = (
            self.patient.user.first_name
            or self.patient.user.email
        )
        return (
            f"{patient_name} - "
            f"{self.interaction_type} - "
            f"{self.status}"
        )