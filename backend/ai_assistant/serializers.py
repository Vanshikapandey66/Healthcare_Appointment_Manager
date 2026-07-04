from rest_framework import serializers
from django.utils import timezone

from .models import AIInteraction


class AIInteractionListSerializer(
    serializers.ModelSerializer
):
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = AIInteraction
        fields = (
            "id",
            "patient_name",
            "interaction_type",
            "status",
            "urgency_level",
            "created_at",
        )

    def get_patient_name(self, obj):
        return (
            obj.patient.user.first_name
            or obj.patient.user.email
        )


class AIInteractionDetailSerializer(
    serializers.ModelSerializer
):
    patient_name = serializers.SerializerMethodField()
    appointment_id = serializers.SerializerMethodField()

    class Meta:
        model = AIInteraction
        fields = "__all__"
        read_only_fields = (
            "status",
            "output_text",
            "tokens_used",
            "retry_count",
            "error_message",
            "model_name",
            "completed_at",
            "created_at",
            "updated_at",
        )

    def get_patient_name(self, obj):
        return (
            obj.patient.user.first_name
            or obj.patient.user.email
        )

    def get_appointment_id(self, obj):
        if obj.appointment:
            return obj.appointment.id
        return None


class AIInteractionCreateSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = AIInteraction
        fields = (
            "appointment",
            "input_text",
            "symptoms",
        )

    def validate_input_text(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Input text cannot be empty."
            )

        blocked_phrases = [
            "ignore previous instructions",
            "reveal system prompt"
        ]

        for phrase in blocked_phrases:
            if phrase in value.lower():
                raise serializers.ValidationError(
                    "Suspicious prompt detected."
                )

        return value

    def validate(self, attrs):
        request = self.context["request"]

        if not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication required."
            )

        if request.user.role != "patient":
            raise serializers.ValidationError(
                "Only patients allowed."
            )

        if not hasattr(
            request.user,
            "patient_profile"
        ):
            raise serializers.ValidationError(
                "Patient profile missing."
            )

        patient = request.user.patient_profile
        appointment = attrs.get("appointment")

        interaction_type = self.context.get(
            "interaction_type"
        )

        symptoms = attrs.get("symptoms")

        # NEW EDGE CASE:
        # whitespace-only symptoms
        if symptoms:
            symptoms = symptoms.strip()

            if not symptoms:
                raise serializers.ValidationError(
                    "Symptoms cannot be empty."
                )

        if appointment:
            if appointment.patient != patient:
                raise serializers.ValidationError(
                    "Invalid appointment."
                )

            if appointment.status == "cancelled":
                raise serializers.ValidationError(
                    "Cancelled appointment not allowed."
                )

            # NEW EDGE CASE:
            # no_show appointment invalid
            if appointment.status == "no_show":
                raise serializers.ValidationError(
                    "No-show appointment not allowed."
                )

            # NEW EDGE CASE:
            # future appointment invalid
            slot_date = appointment.slot.date

            if (
                interaction_type
                in ["post_visit", "follow_up"]
                and slot_date > timezone.localdate()
            ):
                raise serializers.ValidationError(
                    "Future appointment not allowed."
                )

        if (
            interaction_type == "pre_visit"
            and not symptoms
        ):
            raise serializers.ValidationError(
                "Symptoms required for pre-visit."
            )

        if (
            interaction_type
            == "specialist_recommendation"
            and not symptoms
        ):
            raise serializers.ValidationError(
                "Symptoms required."
            )

        if (
            interaction_type == "post_visit"
            and not appointment
        ):
            raise serializers.ValidationError(
                "Appointment required."
            )

        if (
            interaction_type == "follow_up"
            and not appointment
        ):
            raise serializers.ValidationError(
                "Appointment required."
            )

        # NEW EDGE CASE:
        # duplicate pending request
        existing = AIInteraction.objects.filter(
            patient=patient,
            interaction_type=interaction_type,
            status="pending"
        )

        if existing.exists():
            raise serializers.ValidationError(
                "Pending AI request already exists."
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        patient = request.user.patient_profile
        interaction_type = self.context.get(
            "interaction_type"
        )

        interaction = AIInteraction.objects.create(
            patient=patient,
            interaction_type=interaction_type,
            appointment=validated_data.get(
                "appointment"
            ),
            input_text=validated_data[
                "input_text"
            ],
            symptoms=validated_data.get(
                "symptoms"
            ),
        )

        return interaction


class SpecialistRecommendationSerializer(
    serializers.Serializer
):
    symptoms = serializers.CharField()

    def validate_symptoms(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Symptoms required."
            )

        if len(value) > 1000:
            raise serializers.ValidationError(
                "Symptoms too large."
            )

        return value