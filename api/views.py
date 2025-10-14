
from django.contrib.auth.models import Group, User
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import NotFound
from django.utils import timezone
from django.db.models import Q

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from api.serializers import GroupSerializer, UserSerializer, NoticeSerializer, RoutineSerializer, RegisterSerializer, ProfileSerializer, EmailLoginSerializer

from .models import Notice, Routine, Profile
from .permissions import IsAdminUser, ReadOnly

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    Only admin (is_staff=True) can access this.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]




class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    Only admin can access this.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]


class NoticeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Notices.
    - Anyone can read published notices.
    - Only admin can create, update, or delete.
    """

    queryset = Notice.objects.all().order_by("-published_at")
    serializer_class = NoticeSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [ReadOnly()]
        return [IsAdminUser()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["list", "retrieve"]:
            queryset = queryset.filter(published_at__isnull=False)

            #search start:
            
            search_term = self.request.query_params.get("query", None)
            if search_term:
                # search by title and content (case-insensitive)
                queryset = queryset.filter(
                    Q(title_icontains=search_term) | Q(content_icontains=search_term)
                )
            #search end
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            published_at=timezone.now()  # Auto-publish the notice
    )
        


class RoutineViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Routines.
    - Anyone can read routines.
    - Only admin can create, update, or delete.
    """

    queryset = Routine.objects.all().order_by('day', 'start_time')
    serializer_class = RoutineSerializer
    # permission_classes = [permissions.IsAuthenticated]  # default

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [ReadOnly()]  # Anyone can see the routine
        return [IsAdminUser()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Optional: Filter by day if needed
        day = self.request.query_params.get("day", None)
        if day:
            queryset = queryset.filter(day__iexact=day)

        return queryset

    

# Register endpoint (student)
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    """
    Endpoint for registering new users.
    Publicly accessible.
    Validates entered details against AdmissionRecord.
    If successful, creates both User and Profile.
    """

    queryset = User.objects.all()  # always define queryset for CreateAPIView
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()  # This already creates the Profile inside serializer

        # Optional: prepare a custom response
        profile = Profile.objects.filter(user=user).first()
        profile_data = {
            "name": profile.name,
            "email": user.email,
            "semester": profile.semester,
            "roll_no": profile.roll_no,
            "shift": profile.shift,
        }

        return Response({
            "message": "Registration successful.",
            "user": user.email,
            "profile": profile_data
        }, status=status.HTTP_201_CREATED)

        # serializer.is_valid(raise_exception=True)
        # user = serializer.save()

        # # Generate JWT tokens for the new user
        # refresh = RefreshToken.for_user(user)
        # return Response({
        #     "message": "Registration Successful! Welcome aboard.",
        #     "user": UserSerializer(user).data,
        #     "profile": ProfileSerializer(user.profile).data,
        #     "refresh": str(refresh),
        #     "access": str(refresh.access_token),
        # }, status=status.HTTP_201_CREATED)
    


# -------------------- LOGIN (email + password) --------------------
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    Login with email and password.
    Returns JWT tokens.
    """
    permission_classes = [AllowAny]
    serializer_class = EmailLoginSerializer  #Important for browsable API form

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Authenticate using email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": f"Logged in successfully! Welcome back, {user.username}.",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        },status=status.HTTP_200_OK)



    # permission_classes = [AllowAny]

    # def post(self, request):
    #     serializer = EmailLoginSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     user = serializer.validated_data['user']

    #     refresh = RefreshToken.for_user(user)
    #     return Response({
    #         "user": UserSerializer(user).data,
    #         "profile": ProfileSerializer(user.profile).data,
    #         "refresh": str(refresh),
    #         "access": str(refresh.access_token),
    #     }, status=status.HTTP_200_OK)
    


# Profile endpoint (for logged-in users)
class ProfileView(generics.RetrieveUpdateAPIView):
    """
    API for logged-in users to view and update their profile.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]


    def get_object(self):
        user = self.request.user
        profile = getattr(user, "profile", None)
        if profile is None:
            raise NotFound("Profile not found for this user. Please register first.")
        return profile
    # def get_object(self):
    #     user = self.request.user
    #     # Only return existing profile
    #     profile = getattr(user, "profile", None)
    #     if profile is None:
    #         # Don't auto-create empty profiles — just return 404
    #         raise Response(
    #             {"error": "Profile not found for this user. Please register first."},
    #             status=status.HTTP_404_NOT_FOUND
    #         )
    #     return profile

    def get(self, request, *args, **kwargs):
        """
        Override GET to return a proper error message if no profile exists.
        """
        user = request.user
        profile = getattr(user, "profile", None)
        if profile is None:
            return Response(
                {"error": "Profile not found for this user. Please register first."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(profile)
        return Response(serializer.data)
# class ProfileView(generics.RetrieveUpdateAPIView):
#     """
#     API for logged-in users to view and update their profile.
#     """
#     serializer_class = ProfileSerializer
#     permission_classes = [IsAuthenticated]

#     def get_object(self):
#         user = self.request.user
#         # If profile doesn’t exist, create one lazily
#         if not hasattr(user, "profile"):
#             return Profile.objects.create(user=user)
#         return user.profile

    # def get_object(self):
    #     return self.request.user.profile

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """
    Logout endpoint that blacklists the user's refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception:
            return Response(
                {"error": "Invalid or already blacklisted token."},
                status=status.HTTP_400_BAD_REQUEST
            )
    

    # def post(self, request):
    #     try:
    #         refresh_token = request.data["refresh"]
    #         token = RefreshToken(refresh_token)
    #         token.blacklist()
    #         return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
    #     except Exception:
    #         return Response({"error": "Invalid token or already blacklisted."}, status=status.HTTP_400_BAD_REQUEST)


