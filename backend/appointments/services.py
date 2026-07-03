from datetime import datetime, timedelta
from django.utils import timezone
from appointments.models import AvailabilitySlot


def generate_slots_for_doctor(doctor, days=30):

    # Edge Case 1:
    # Unapproved doctor should not get slots
    if doctor.approval_status != "approved":
        return

    today = timezone.localdate()
    current_time = timezone.localtime().time()

    for i in range(days):
        current_date = today + timedelta(days=i)

        weekday = current_date.strftime("%A").lower()

        # Edge Case 2:
        # Full-day leave skip
        full_day_leave = doctor.leaves.filter(
            leave_date=current_date,
            is_full_day=True
        ).exists()

        if full_day_leave:
            continue

        availabilities = doctor.availabilities.filter(
            day=weekday
        )

        for availability in availabilities:

            current_start = datetime.combine(
                current_date,
                availability.start_time
            )

            availability_end = datetime.combine(
                current_date,
                availability.end_time
            )

            slot_duration = timedelta(
                minutes=availability.slot_duration
            )

            while current_start + slot_duration <= availability_end:

                slot_end = current_start + slot_duration

                # Edge Case 3:
                # Skip past-time slots for today
                if current_date == today:
                    if slot_end.time() <= current_time:
                        current_start += slot_duration
                        continue

                # Edge Case 4:
                # Partial leave skip
                partial_leaves = doctor.leaves.filter(
                    leave_date=current_date,
                    is_full_day=False
                )

                skip_slot = False

                for leave in partial_leaves:
                    if (
                        current_start.time() < leave.end_time
                        and slot_end.time() > leave.start_time
                    ):
                        skip_slot = True
                        break

                if not skip_slot:
                    AvailabilitySlot.objects.get_or_create(
                        doctor=doctor,
                        date=current_date,
                        start_time=current_start.time(),
                        end_time=slot_end.time()
                    )

                current_start += slot_duration