from django.contrib import admin

from .models import AIInteraction


@admin.register(AIInteraction)
class AIInteractionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "interaction_type",
        "status",
        "urgency_level",
        "tokens_used",
        "retry_count",
        "created_at",
        "completed_at",
    )

    list_filter = (
        "interaction_type",
        "status",
        "urgency_level",
        "created_at",
    )

    search_fields = (
        "patient__user__email",
        "patient__user__first_name",
        "input_text",
        "output_text",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "completed_at",
        "tokens_used",
        "retry_count",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "patient",
                    "appointment",
                    "interaction_type",
                    "status",
                )
            }
        ),

        (
            "Input",
            {
                "fields": (
                    "input_text",
                    "symptoms",
                )
            }
        ),

        (
            "AI Output",
            {
                "fields": (
                    "output_text",
                    "urgency_level",
                    "recommended_specialization",
                )
            }
        ),

        (
            "AI Metadata",
            {
                "fields": (
                    "model_name",
                    "tokens_used",
                    "retry_count",
                    "error_message",
                )
            }
        ),

        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "completed_at",
                )
            }
        ),
    )