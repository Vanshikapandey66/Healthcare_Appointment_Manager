from django.urls import path

from .views import (
    PreVisitAPIView,
    PostVisitAPIView,
    FollowUpAPIView,
    SpecialistRecommendationAPIView,
    InteractionHistoryAPIView,
    InteractionDetailAPIView,
    RetryInteractionAPIView,
    FailedInteractionsAPIView,
    AIAnalyticsAPIView
)

urlpatterns = [
    path(
        "pre-visit/",
        PreVisitAPIView.as_view(),
        name="ai-pre-visit"
    ),

    path(
        "post-visit/",
        PostVisitAPIView.as_view(),
        name="ai-post-visit"
    ),

    path(
        "follow-up/",
        FollowUpAPIView.as_view(),
        name="ai-follow-up"
    ),

    path(
        "specialist-recommendation/",
        SpecialistRecommendationAPIView.as_view(),
        name="ai-specialist-recommendation"
    ),

    path(
        "history/",
        InteractionHistoryAPIView.as_view(),
        name="ai-history"
    ),

    path(
        "history/<int:interaction_id>/",
        InteractionDetailAPIView.as_view(),
        name="ai-detail"
    ),

    path(
        "retry/<int:interaction_id>/",
        RetryInteractionAPIView.as_view(),
        name="ai-retry"
    ),

    path(
        "admin/failed/",
        FailedInteractionsAPIView.as_view(),
        name="ai-failed"
    ),

    path(
        "admin/analytics/",
        AIAnalyticsAPIView.as_view(),
        name="ai-analytics"
    ),
]