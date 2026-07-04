from django.urls import path

from .views import (
    PostVisitLLMView,
    PreVisitLLMView,
    SlotListCreateView,
    MySlotsView,
    SlotDetailView,
    AppointmentCreateView,
    MyAppointmentsView,
    AppointmentDetailView,
    AppointmentStatusUpdateView,
    DoctorAppointmentsView,
    AllAppointmentsView,
    AppointmentRescheduleView
)

urlpatterns = [
    # SLOT APIs
    path(
        "slots/",
        SlotListCreateView.as_view(),
        name="slot-list-create"
    ),

    path(
        "slots/my/",
        MySlotsView.as_view(),
        name="my-slots"
    ),

    path(
        "slots/<int:slot_id>/",
        SlotDetailView.as_view(),
        name="slot-detail"
    ),

    # APPOINTMENT APIs
    path(
        "book/",
        AppointmentCreateView.as_view(),
        name="book-appointment"
    ),

    path(
        "my/",
        MyAppointmentsView.as_view(),
        name="my-appointments"
    ),

    path(
        "<int:appointment_id>/",
        AppointmentDetailView.as_view(),
        name="appointment-detail"
    ),

    path(
        "<int:appointment_id>/status/",
        AppointmentStatusUpdateView.as_view(),
        name="appointment-status-update"
    ),

    path(
        "doctor/",
        DoctorAppointmentsView.as_view(),
        name="doctor-appointments"
    ),

    path(
        "admin/all/",
        AllAppointmentsView.as_view(),
        name="admin-all-appointments"
    ),

    path(
    "appointments/<int:appointment_id>/reschedule/",
    AppointmentRescheduleView.as_view(),
    name="appointment-reschedule"
    ),

    path("ai/pre-visit/", PreVisitLLMView.as_view()),
    path("ai/post-visit/", PostVisitLLMView.as_view()),
    ]