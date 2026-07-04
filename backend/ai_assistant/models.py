from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from patients.models import PatientProfile
from appointments.models import Appointment
from doctors.models import Specialization


class AIInteraction(models.Model):
    INTERACTION_CHOICES = (
        ("general_chat", "General Chat"),
        ("pre_visit", "Pre Visit"),
        ("post_visit", "Post Visit"),
        ("follow_up", "Follow Up"),
        ("specialist_recommendation", "Specialist Recommendation"),
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
        max_length=50,
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

        # Edge Case 1
        if self.patient.user.role != "patient":
            raise ValidationError(
                "Only patients can use AI assistant."
            )

        # Edge Case 2
        if not self.input_text.strip():
            raise ValidationError(
                "Input text cannot be empty."
            )

        # Edge Case 3
        if len(self.input_text) > 5000:
            raise ValidationError(
                "Input text exceeds maximum length."
            )

        # Edge Case 4
        if (
            self.interaction_type == "post_visit"
            and not self.appointment
        ):
            raise ValidationError(
                "Post-visit interaction requires appointment."
            )

        # Edge Case 5
        if (
            self.appointment
            and self.appointment.patient != self.patient
        ):
            raise ValidationError(
                "Appointment does not belong to patient."
            )

        # Edge Case 6
        if (
            self.interaction_type == "pre_visit"
            and not self.symptoms
        ):
            raise ValidationError(
                "Pre-visit requires symptoms."
            )

        # Edge Case 7
        if (
            self.interaction_type
            == "specialist_recommendation"
            and not self.symptoms
        ):
            raise ValidationError(
                "Specialist recommendation requires symptoms."
            )

        # Edge Case 8
        if self.symptoms and len(self.symptoms) > 1000:
            raise ValidationError(
                "Symptoms too large."
            )

        # Edge Case 9
        if (
            self.interaction_type == "post_visit"
            and self.appointment
            and self.appointment.status == "cancelled"
        ):
            raise ValidationError(
                "Cancelled appointment invalid."
            )

        # Edge Case 10
        if (
            self.interaction_type == "post_visit"
            and self.appointment
        ):
            slot_date = self.appointment.slot.date

            if slot_date > timezone.localdate():
                raise ValidationError(
                    "Post-visit not allowed before appointment."
                )

        # Edge Case 11
        if (
            self.status == "completed"
            and not self.output_text
        ):
            raise ValidationError(
                "Completed interaction requires output."
            )

        # Edge Case 12
        if (
            self.status == "pending"
            and self.output_text
        ):
            raise ValidationError(
                "Pending interaction cannot have output."
            )

        # Edge Case 13
        if (
            self.status == "failed"
            and not self.error_message
        ):
            raise ValidationError(
                "Failed interaction requires error message."
            )

        # Edge Case 14
        if self.retry_count > 3:
            raise ValidationError(
                "Retry count cannot exceed 3."
            )

        # Edge Case 15
        if (
            self.status == "pending"
            and self.tokens_used
        ):
            raise ValidationError(
                "Pending interaction cannot have token count."
            )

        # Edge Case 16
        if (
            self.status == "completed"
            and not self.model_name
        ):
            raise ValidationError(
                "Completed interaction must store model name."
            )

        # Edge Case 17
        if (
            self.status == "completed"
            and not self.completed_at
        ):
            raise ValidationError(
                "Completed interaction needs completed_at."
            )

        # Edge Case 18
        if (
            self.status == "pending"
            and self.completed_at
        ):
            raise ValidationError(
                "Pending interaction cannot have completed_at."
            )

        # Edge Case 19
        if (
            self.status == "failed"
            and self.output_text
        ):
            raise ValidationError(
                "Failed interaction cannot have output."
            )

        # Edge Case 20
        if (
            self.completed_at
            and self.created_at
            and self.completed_at < self.created_at
        ):
            raise ValidationError(
                "Completion time invalid."
            )

        # Edge Case 21
        active_requests = AIInteraction.objects.filter(
            patient=self.patient,
            interaction_type=self.interaction_type,
            status="pending"
        ).exclude(id=self.id)

        if active_requests.exists():
            raise ValidationError(
                "Another pending request already exists."
            )

        # Edge Case 22
        if (
            self.urgency_level == "emergency"
            and not self.output_text
        ):
            raise ValidationError(
                "Emergency response must contain output."
            )

        # Edge Case 23
        if (
            self.status == "completed"
            and self.error_message
        ):
            raise ValidationError(
                "Completed interaction cannot have error."
            )

        # Edge Case 24
        if (
            self.status == "failed"
            and self.completed_at
        ):
            raise ValidationError(
                "Failed interaction cannot have completed_at."
            )

        # Edge Case 25
        if (
            self.tokens_used is not None
            and self.tokens_used < 0
        ):
            raise ValidationError(
                "Tokens cannot be negative."
            )

        # Edge Case 26
        if (
            self.recommended_specialization
            and self.interaction_type not in
            ["pre_visit", "specialist_recommendation"]
        ):
            raise ValidationError(
                "Specialization recommendation invalid for this interaction type."
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