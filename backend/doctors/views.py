from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import DoctorRegisterSerializer

from .models import (
    Specialization,
    DoctorProfile,
    DoctorAvailability,
    DoctorLeave
)

from .serializers import (
    SpecializationSerializer,
    DoctorProfileListSerializer,
    DoctorProfileDetailSerializer,
    DoctorProfileUpdateSerializer,
    DoctorAvailabilitySerializer,
    DoctorLeaveSerializer,
    DoctorApprovalSerializer
)

from appointments.models import Appointment


class SpecializationListView(APIView):
    def get(self, request):
        specializations = Specialization.objects.all()
        serializer = SpecializationSerializer(
            specializations,
            many=True
        )
        return Response(serializer.data)


class DoctorListView(APIView):
    def get(self, request):
        doctors = DoctorProfile.objects.filter(
            approval_status="approved"
        )

        specialization = request.query_params.get(
            "specialization"
        )
        city = request.query_params.get("city")

        if specialization:
            doctors = doctors.filter(
                specialization_id=specialization
            )

        if city:
            doctors = doctors.filter(
                city__iexact=city
            )

        serializer = DoctorProfileListSerializer(
            doctors,
            many=True
        )

        return Response(serializer.data)


class DoctorDetailView(APIView):
    def get(self, request, doctor_id):
        try:
            doctor = DoctorProfile.objects.get(
                id=doctor_id,
                approval_status="approved"
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"error": "Doctor not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorProfileDetailSerializer(
            doctor
        )
        return Response(serializer.data)


class MyDoctorProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorProfileDetailSerializer(
            request.user.doctor_profile
        )

        return Response(serializer.data)

    def patch(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        profile = request.user.doctor_profile

        protected_fields = [
            "license_number",
            "specialization"
        ]

        if profile.approval_status == "approved":
            for field in protected_fields:
                if field in request.data:
                    return Response(
                        {
                            "error":
                            f"Approved doctors cannot modify {field}."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        serializer = DoctorProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "message": "Profile updated successfully.",
                    "data": serializer.data
                }
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class AvailabilityListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        availabilities = DoctorAvailability.objects.filter(
            doctor=request.user.doctor_profile
        )

        serializer = DoctorAvailabilitySerializer(
            availabilities,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorAvailabilitySerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class AvailabilityDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, availability_id):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            availability = DoctorAvailability.objects.get(
                id=availability_id,
                doctor=request.user.doctor_profile
            )
        except DoctorAvailability.DoesNotExist:
            return Response(
                {"error": "Availability not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorAvailabilitySerializer(
            availability,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, availability_id):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            availability = DoctorAvailability.objects.get(
                id=availability_id,
                doctor=request.user.doctor_profile
            )
        except DoctorAvailability.DoesNotExist:
            return Response(
                {"error": "Availability not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        scheduled_appointments = Appointment.objects.filter(
            slot__doctor=request.user.doctor_profile,
            status="scheduled"
        )

        if scheduled_appointments.exists():
            return Response(
                {
                    "error":
                    "Cannot delete availability with scheduled appointments."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        availability.delete()

        return Response(
            {"message": "Availability deleted successfully."}
        )


class LeaveListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        leaves = DoctorLeave.objects.filter(
            doctor=request.user.doctor_profile
        )

        serializer = DoctorLeaveSerializer(
            leaves,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        leave_date = request.data.get("leave_date")

        scheduled_appointments = Appointment.objects.filter(
            slot__doctor=request.user.doctor_profile,
            slot__date=leave_date,
            status="scheduled"
        )

        if scheduled_appointments.exists():
            return Response(
                {
                    "error":
                    "Scheduled appointments already exist on this date."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DoctorLeaveSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class LeaveDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, leave_id):
        if request.user.role != "doctor":
            return Response(
                {"error": "Only doctors allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            leave = DoctorLeave.objects.get(
                id=leave_id,
                doctor=request.user.doctor_profile
            )
        except DoctorLeave.DoesNotExist:
            return Response(
                {"error": "Leave not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        leave.delete()

        return Response(
            {"message": "Leave deleted successfully."}
        )


class DoctorApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, doctor_id):
        if request.user.role != "admin":
            return Response(
                {"error": "Only admin allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            doctor = DoctorProfile.objects.get(
                id=doctor_id
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"error": "Doctor not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if doctor.approval_status == "rejected":
            return Response(
                {
                    "error":
                    "Rejected doctor cannot be re-approved."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DoctorApprovalSerializer(
            doctor,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            new_status = serializer.validated_data["approval_status"]

            doctor.approval_status = new_status

            if new_status == "approved":
                doctor.approved_by = request.user

            doctor.save()

            return Response({
                "message": "Approval updated successfully.",
                "data": {
                    "approval_status": doctor.approval_status
                }
            })

            return Response(
                {
                    "message": "Approval updated successfully.",
                    "data": serializer.data
                }
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
class DoctorRegisterView(APIView):

    def post(self, request):
        serializer = DoctorRegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():
            doctor = serializer.save()

            return Response(
                {
                    "message":
                    "Doctor registered successfully. Waiting for admin approval.",
                    "doctor_id": doctor.id
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )