from django.contrib import admin
from .models import Appointment, AvailabilitySlot


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "slot", "status", "booked_at")
    list_filter = ("status",)
    search_fields = ("patient__user__email",)


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("doctor", "date", "start_time", "end_time")
    search_fields = ("doctor__full_name",)