from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import PatientProfile
from .serializers import PatientProfileSerializer


class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, request):
        """
        Common helper function for profile fetch
        """

        if request.user.role != "patient":
            return None, Response(
                {
                    "error":
                    "Only patients can access this API."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            profile = request.user.patient_profile
            return profile, None

        except PatientProfile.DoesNotExist:
            return None, Response(
                {
                    "error":
                    "Patient profile not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request):
        profile, error_response = self.get_profile(
            request
        )

        if error_response:
            return error_response

        serializer = PatientProfileSerializer(
            profile
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def put(self, request):
        profile, error_response = self.get_profile(
            request
        )

        if error_response:
            return error_response

        # Edge Case 3: empty body
        if not request.data:
            return Response(
                {
                    "error":
                    "No data provided for update."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientProfileSerializer(
            profile,
            data=request.data,
            partial=False
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "message":
                    "Profile updated successfully.",
                    "data":
                    serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request):
        profile, error_response = self.get_profile(
            request
        )

        if error_response:
            return error_response

        # Edge Case 4: empty body
        if not request.data:
            return Response(
                {
                    "error":
                    "No data provided for update."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "message":
                    "Profile updated successfully.",
                    "data":
                    serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )