from django.contrib import admin
from .models import (
    Specialization,
    DoctorProfile,
    DoctorAvailability,
    DoctorLeave
)


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "specialization",
        "approval_status",
        "clinic_name",
        "city"
    )

    list_filter = (
        "approval_status",
        "specialization",
        "city"
    )

    search_fields = (
        "full_name",
        "license_number",
        "user__email"
    )


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "day",
        "start_time",
        "end_time",
        "slot_duration"
    )

    list_filter = ("day",)


@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "leave_date",
        "is_full_day"
    )

    list_filter = (
        "leave_date",
        "is_full_day"
    )