import json
import time
import re
from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone
from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from openai import OpenAI

from doctors.models import Specialization
from .models import AIInteraction
from .serializers import (
    AIInteractionCreateSerializer,
    AIInteractionListSerializer,
    AIInteractionDetailSerializer
)

MAX_ALLOWED_TOKENS = 4000
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

def get_openai_client():
    try:
        return OpenAI()
    except Exception:
        raise ValidationError(
            "AI service unavailable."
        )


def estimate_tokens(text):
    return len(text) // 4

def sanitize_output(text):
    return re.sub(r"<.*?>", "", text)

def build_prompt(interaction_type, input_text, symptoms=None):
    prompt = f"""
    Interaction Type: {interaction_type}

    Patient Input:
    {input_text}
    """

    if symptoms:
        prompt += f"\nSymptoms:\n{symptoms}\n"

    prompt += """
Return ONLY valid JSON:
{
 "summary": "...",
 "urgency": "low/medium/high/emergency",
 "specialization": "specialization name or null"
}
"""
    return prompt


def call_openai(prompt):
    for attempt in range(MAX_RETRIES):
        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                timeout=REQUEST_TIMEOUT
            )

            if not response.choices:
                raise ValidationError("Invalid AI response.")

            return response.choices[0].message.content

        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise

            wait = 2 ** attempt
            time.sleep(wait)


def parse_ai_response(response_text):
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        raise ValidationError("AI returned invalid JSON.")

    required_fields = [
        "summary",
        "urgency",
        "specialization"
    ]

    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing AI field: {field}")

    return data


def validate_ai_output(ai_data):
    valid_urgencies = [
        "low",
        "medium",
        "high",
        "emergency"
    ]

    urgency = ai_data["urgency"].lower()

    if urgency not in valid_urgencies:
        raise ValidationError("Invalid urgency from AI.")

    summary = sanitize_output(
    ai_data["summary"]
).strip()

    if not summary:
        raise ValidationError("AI summary empty.")

    specialization_name = ai_data["specialization"]
    specialization_obj = None

    if specialization_name:
        try:
            specialization_obj = Specialization.objects.get(
                name__iexact=specialization_name
            )
        except Specialization.DoesNotExist:
            raise ValidationError(
                "AI returned invalid specialization."
            )

    if urgency == "emergency":
        summary += "\nSeek emergency medical care immediately."

    return {
        "summary": summary,
        "urgency": urgency,
        "specialization": specialization_obj
    }


def process_ai_interaction(serializer, interaction_type):
    request = serializer.context["request"]
    patient = request.user.patient_profile

    with transaction.atomic():
        existing = (
            AIInteraction.objects
            .select_for_update()
            .filter(
                patient=patient,
                interaction_type=interaction_type,
                status="pending"
            )
        )

        if existing.exists():
            raise ValidationError(
                "Another pending AI request exists."
            )

        interaction = serializer.save()

    prompt = build_prompt(
        interaction_type=interaction_type,
        input_text=interaction.input_text,
        symptoms=interaction.symptoms
    )

    estimated_tokens = estimate_tokens(prompt)

    if estimated_tokens > MAX_ALLOWED_TOKENS:
        interaction.status = "failed"
        interaction.error_message = "Prompt exceeds token limit."
        interaction.retry_count += 1
        interaction.save()

        raise ValidationError("Prompt too large.")

    try:
        response = call_openai(prompt)
        ai_data = parse_ai_response(response)
        validated = validate_ai_output(ai_data)

        interaction.output_text = validated["summary"]
        interaction.urgency_level = validated["urgency"]
        interaction.recommended_specialization = (
            validated["specialization"]
        )
        interaction.status = "completed"
        interaction.model_name = "gpt-4o-mini"
        interaction.tokens_used = estimated_tokens
        interaction.completed_at = timezone.now()
        interaction.save()

        return interaction

    except Exception as e:
        interaction.status = "failed"
        interaction.retry_count += 1

        error_text = str(e)

        if len(error_text) > 1000:
            error_text = error_text[:1000]

        interaction.error_message = error_text
        interaction.save()

        raise ValidationError("AI processing failed.")


class PreVisitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AIInteractionCreateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            interaction = process_ai_interaction(
                serializer,
                "pre_visit"
            )

            return Response(
                AIInteractionDetailSerializer(
                    interaction
                ).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=400)


class PostVisitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients allowed."},
                status=403
            )

        serializer = AIInteractionCreateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            appointment = serializer.validated_data.get(
                "appointment"
            )

            if not appointment:
                return Response(
                    {"error": "Post-visit requires appointment."},
                    status=400
                )

            if appointment.status != "completed":
                return Response(
                    {"error": "Appointment must be completed."},
                    status=400
                )

            interaction = process_ai_interaction(
                serializer,
                "post_visit"
            )

            return Response(
                AIInteractionDetailSerializer(
                    interaction
                ).data,
                status=201
            )

        return Response(serializer.errors, status=400)


class FollowUpAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients allowed."},
                status=403
            )

        serializer = AIInteractionCreateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            appointment = serializer.validated_data.get(
                "appointment"
            )

            if not appointment:
                return Response(
                    {
                        "error":
                        "Follow-up requires completed appointment."
                    },
                    status=400
                )


            interaction = process_ai_interaction(
                serializer,
                "follow_up"
            )

            return Response(
                AIInteractionDetailSerializer(
                    interaction
                ).data,
                status=201
            )

        return Response(serializer.errors, status=400)


class SpecialistRecommendationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "patient":
            return Response(
                {"error": "Only patients allowed."},
                status=403
            )

        serializer = AIInteractionCreateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            interaction = process_ai_interaction(
                serializer,
                "pre_visit"
            )

            return Response({
                "specialization":
                    interaction.recommended_specialization.name
                    if interaction.recommended_specialization
                    else None,
                "urgency":
                    interaction.urgency_level
            })

        return Response(serializer.errors, status=400)


class InteractionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "patient":
            return Response({"error": "Only patients allowed."}, status=403)
          
        try:
            page = int(
                request.query_params.get("page", 1)
            )
            page_size = int(
                request.query_params.get(
                    "page_size",
                    20
                )
            )
        except ValueError:
            return Response(
                {
                    "error":
                    "Invalid pagination parameters."
                },
                status=400
            )

        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 20

        if page_size > 100:
            page_size = 100
            

        start = (page - 1) * page_size
        end = start + page_size

        queryset = (
            AIInteraction.objects
            .filter(patient=request.user.patient_profile)
            .order_by("-created_at")
        )

        total = queryset.count()

        serializer = AIInteractionListSerializer(
            queryset[start:end],
            many=True
        )

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": end < total,
            "results": serializer.data
        })


class InteractionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, interaction_id):
        if request.user.role != "patient":
            return Response({"error": "Only patients allowed."}, status=403)

        try:
            interaction = AIInteraction.objects.get(
                id=interaction_id,
                patient=request.user.patient_profile
            )
        except AIInteraction.DoesNotExist:
            return Response(
                {"error": "Interaction not found."},
                status=404
            )

        serializer = AIInteractionDetailSerializer(interaction)
        return Response(serializer.data)


class RetryInteractionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, interaction_id):
        if request.user.role != "patient":
            return Response({"error": "Only patients allowed."}, status=403)

        try:
            with transaction.atomic():
                interaction = (
                    AIInteraction.objects
                    .select_for_update()
                    .get(
                        id=interaction_id,
                        patient=request.user.patient_profile
                    )
                )

                if interaction.status != "failed":
                    return Response(
                        {"error": "Only failed interactions can be retried."},
                        status=400
                    )

                if interaction.retry_count >= MAX_RETRIES:
                    return Response(
                        {"error": "Maximum retry limit reached."},
                        status=400
                    )

                interaction.status = "pending"
                interaction.error_message = None
                interaction.save()

        except AIInteraction.DoesNotExist:
            return Response({"error": "Interaction not found."}, status=404)

        prompt = build_prompt(
            interaction.interaction_type,
            interaction.input_text,
            interaction.symptoms
        )

        estimated_tokens = estimate_tokens(prompt)

        if estimated_tokens > MAX_ALLOWED_TOKENS:
            interaction.status = "failed"
            interaction.retry_count += 1
            interaction.error_message = (
                "Prompt exceeds token limit."
            )
            interaction.save()

            return Response(
                {"error": "Prompt too large."},
                status=400
            )

        try:
            response = call_openai(prompt)
            ai_data = parse_ai_response(response)
            validated = validate_ai_output(ai_data)

            interaction.output_text = validated["summary"]
            interaction.urgency_level = validated["urgency"]
            interaction.recommended_specialization = validated["specialization"]
            interaction.status = "completed"
            interaction.completed_at = timezone.now()
            interaction.model_name = "gpt-4o-mini"
            interaction.tokens_used = estimate_tokens(prompt)
            interaction.save()

            return Response(
                AIInteractionDetailSerializer(interaction).data
            )

        except Exception as e:
            interaction.status = "failed"
            interaction.retry_count += 1
            error_text = str(e)

            if len(error_text) > 1000:
                error_text = error_text[:1000]

            interaction.error_message = error_text
            interaction.save()

            return Response({"error": "Retry failed."}, status=400)


class FailedInteractionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            return Response({"error": "Only admin allowed."}, status=403)

        interactions = (
            AIInteraction.objects
            .filter(status="failed")
            .order_by("-created_at")
        )

        serializer = AIInteractionListSerializer(
            interactions,
            many=True
        )

        return Response(serializer.data)


class AIAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            return Response({"error": "Only admin allowed."}, status=403)

        total = AIInteraction.objects.count()
        completed = AIInteraction.objects.filter(status="completed").count()
        failed = AIInteraction.objects.filter(status="failed").count()

        avg_tokens = (
            AIInteraction.objects
            .filter(tokens_used__isnull=False)
            .aggregate(avg=Avg("tokens_used"))["avg"]
        ) or 0

        interaction_types = (
            AIInteraction.objects
            .values("interaction_type")
            .annotate(count=Count("id"))
        )

        return Response({
            "total_requests": total,
            "completed_requests": completed,
            "failed_requests": failed,
            "average_tokens_used": round(avg_tokens, 2),
            "interaction_breakdown": interaction_types
        })