from rest_framework import serializers
from users.models import User
from .models import (
    Specialization,
    DoctorProfile,
    DoctorAvailability,
    DoctorLeave,
    DoctorProfile, 
    Specialization
)


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = [
            "id",
            "name"
        ]


class DoctorProfileListSerializer(serializers.ModelSerializer):
    specialization = serializers.StringRelatedField()
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "full_name",
            "specialization",
            "clinic_name",
            "city",
            "consultation_fee",
            "experience_years",
            "approval_status",
            "email"
        ]


class DoctorProfileDetailSerializer(serializers.ModelSerializer):
    specialization = SpecializationSerializer(
        read_only=True
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    phone_number = serializers.CharField(
        source="user.phone_number",
        read_only=True
    )

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "full_name",
            "specialization",
            "license_number",
            "clinic_name",
            "city",
            "consultation_fee",
            "experience_years",
            "approval_status",
            "approved_by",
            "email",
            "phone_number"
        ]


class DoctorProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = [
            "full_name",
            "specialization",
            "license_number",
            "clinic_name",
            "city",
            "consultation_fee",
            "experience_years"
        ]

    def validate_consultation_fee(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Consultation fee must be greater than zero."
            )
        return value

    def validate_experience_years(self, value):
        if value > 80:
            raise serializers.ValidationError(
                "Invalid experience years."
            )
        return value


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailability
        fields = [
            "id",
            "doctor",
            "day",
            "start_time",
            "end_time",
            "slot_duration"
        ]
        read_only_fields = [
            "doctor"
        ]

    def create(self, validated_data):
        request = self.context.get("request")

        validated_data["doctor"] = (
            request.user.doctor_profile
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("doctor", None)
        return super().update(instance, validated_data)


class DoctorLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorLeave
        fields = [
            "id",
            "doctor",
            "leave_date",
            "is_full_day",
            "start_time",
            "end_time",
            "reason"
        ]
        read_only_fields = [
            "doctor"
        ]

    def create(self, validated_data):
        request = self.context.get("request")

        validated_data["doctor"] = (
            request.user.doctor_profile
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("doctor", None)
        return super().update(instance, validated_data)


class DoctorApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = [
            "approval_status"
        ]

    def validate_approval_status(self, value):
        allowed_status = [
            "pending",
            "approved",
            "rejected"
        ]

        if value not in allowed_status:
            raise serializers.ValidationError(
                "Invalid approval status."
            )

        return value
    
class DoctorRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField()

    full_name = serializers.CharField()
    specialization = serializers.IntegerField()
    license_number = serializers.CharField()
    clinic_name = serializers.CharField()
    city = serializers.CharField()
    consultation_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    experience_years = serializers.IntegerField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email already registered."
            )
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "Phone number already registered."
            )
        return value

    def validate_specialization(self, value):
        try:
            specialization = Specialization.objects.get(id=value)
        except Specialization.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid specialization."
            )

        return specialization

    def validate_experience_years(self, value):
        if value < 0 or value > 80:
            raise serializers.ValidationError(
                "Invalid experience years."
            )
        return value

    def create(self, validated_data):
        specialization = validated_data.pop("specialization")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            phone_number=validated_data["phone_number"],
            role="doctor",
            password=password
        )

        doctor = DoctorProfile.objects.create(
            user=user,
            specialization=specialization,
            full_name=validated_data["full_name"],
            license_number=validated_data["license_number"],
            clinic_name=validated_data["clinic_name"],
            city=validated_data["city"],
            consultation_fee=validated_data["consultation_fee"],
            experience_years=validated_data["experience_years"],
            approval_status="pending"
        )

        return doctor