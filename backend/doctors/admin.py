from django.contrib import admin
from .models import DoctorProfile

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
        "clinic_name"
    )

    def save_model(self, request, obj, form, change):
        if obj.approval_status == "approved":
            obj.approved_by = request.user
        super().save_model(request, obj, form, change)
