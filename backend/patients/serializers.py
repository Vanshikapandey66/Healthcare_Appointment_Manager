from rest_framework import serializers
from .models import PatientProfile
from datetime import date


class PatientProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    phone_number = serializers.CharField(
        source="user.phone_number",
        read_only=True
    )

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "email",
            "phone_number",
            "date_of_birth",
            "gender"
        ]

    def validate_date_of_birth(self, value):
        if value:
            # Edge Case 1: future DOB
            if value > date.today():
                raise serializers.ValidationError(
                    "Date of birth cannot be in future."
                )

            # Edge Case 2: unrealistic DOB
            if value.year < 1900:
                raise serializers.ValidationError(
                    "Invalid date of birth."
                )

        return value