from django.urls import path

from .views import (
    SpecializationListView,
    DoctorListView,
    DoctorDetailView,
    MyDoctorProfileView,
    AvailabilityListCreateView,
    AvailabilityDetailView,
    LeaveListCreateView,
    LeaveDetailView,
    DoctorApprovalView,
    DoctorRegisterView
)

urlpatterns = [
    # Public APIs
    path(
    "register/",
    DoctorRegisterView.as_view(),
    name="doctor-register"
    ),

    path(
        "specializations/",
        SpecializationListView.as_view(),
        name="specialization-list"
    ),

    path(
        "",
        DoctorListView.as_view(),
        name="doctor-list"
    ),

    path(
        "<int:doctor_id>/",
        DoctorDetailView.as_view(),
        name="doctor-detail"
    ),

    # Doctor private APIs
    path(
        "me/profile/",
        MyDoctorProfileView.as_view(),
        name="my-doctor-profile"
    ),

    path(
        "availability/",
        AvailabilityListCreateView.as_view(),
        name="availability-list-create"
    ),

    path(
        "availability/<int:availability_id>/",
        AvailabilityDetailView.as_view(),
        name="availability-detail"
    ),

    path(
        "leaves/",
        LeaveListCreateView.as_view(),
        name="leave-list-create"
    ),

    path(
        "leaves/<int:leave_id>/",
        LeaveDetailView.as_view(),
        name="leave-detail"
    ),

    # Admin API
    path(
        "<int:doctor_id>/approval/",
        DoctorApprovalView.as_view(),
        name="doctor-approval"
    ),
]