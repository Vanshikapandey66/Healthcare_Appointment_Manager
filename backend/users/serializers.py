from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from users.models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile, Specialization


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True
    )

    full_name = serializers.CharField(required=False)
    specialization = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(),
        required=False
    )
    license_number = serializers.CharField(required=False)
    clinic_name = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    consultation_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    experience_years = serializers.IntegerField(
        required=False
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "phone_number",
            "role",
            "full_name",
            "specialization",
            "license_number",
            "clinic_name",
            "city",
            "consultation_fee",
            "experience_years"
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )
        return value

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "Phone number must contain digits only."
            )

        if len(value) < 10 or len(value) > 15:
            raise serializers.ValidationError(
                "Phone number length must be between 10 and 15."
            )

        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role(self, value):
        if value == "admin":
            raise serializers.ValidationError(
                "Admin registration not allowed."
            )
        return value

    def validate(self, attrs):
        role = attrs.get("role")

        if role == "doctor":
            required_fields = [
                "full_name",
                "specialization",
                "license_number",
                "clinic_name",
                "city",
                "consultation_fee",
                "experience_years"
            ]

            missing_fields = []

            for field in required_fields:
                if attrs.get(field) in [None, ""]:
                    missing_fields.append(field)

            if missing_fields:
                raise serializers.ValidationError(
                    {
                        "missing_fields":
                        f"Doctor registration requires: {', '.join(missing_fields)}"
                    }
                )

            license_number = attrs.get("license_number")

            if DoctorProfile.objects.filter(
                license_number=license_number
            ).exists():
                raise serializers.ValidationError(
                    {
                        "license_number":
                        "License number already exists."
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")

        doctor_data = {
            "full_name": validated_data.pop(
                "full_name",
                None
            ),
            "specialization": validated_data.pop(
                "specialization",
                None
            ),
            "license_number": validated_data.pop(
                "license_number",
                None
            ),
            "clinic_name": validated_data.pop(
                "clinic_name",
                None
            ),
            "city": validated_data.pop(
                "city",
                None
            ),
            "consultation_fee": validated_data.pop(
                "consultation_fee",
                None
            ),
            "experience_years": validated_data.pop(
                "experience_years",
                None
            ),
        }

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if user.role == "patient":
            PatientProfile.objects.create(
                user=user
            )

        elif user.role == "doctor":
            DoctorProfile.objects.create(
                user=user,
                **doctor_data
            )

        return user
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "role"
        ]