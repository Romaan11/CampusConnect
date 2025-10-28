
from django.contrib.auth.models import Group, User
from rest_framework import viewsets, generics, status, permissions, views
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import NotFound
from django.utils import timezone
from django.db.models import Q  
from rest_framework.decorators import api_view, permission_classes
from .utils import send_fcm_notification

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from api.serializers import GroupSerializer, UserSerializer, NoticeSerializer, RoutineSerializer, RegisterSerializer, ProfileSerializer, EmailLoginSerializer, EventSerializer

from .models import Notice, Routine, Profile, DeviceToken, Event
from .permissions import IsAdminUser, ReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser #later added
# from NOTICE.firebase_config import firebase_admin
# from firebase_admin import messaging



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
    - Normal users see only routines of their semester.
    - Anyone can read routines.
    - Only admin can create, update, or delete.
    - Optional: filter by day (e.g., ?day=Monday)
    """

    queryset = Routine.objects.all().order_by('day', 'start_time')
    serializer_class = RoutineSerializer
    # permission_classes = [permissions.IsAuthenticated]  # default

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [ReadOnly()]  # Anyone can see the routine
        return [permissions.IsAdminUser()]  # Only admin can edit

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        #  Filter where Normal users see only routines of their semester
        if user.is_authenticated and not user.is_staff:
            try:
                profile = Profile.objects.get(user=user)
                queryset = queryset.filter(semester=str(profile.semester))
            except Profile.DoesNotExist:
                queryset = queryset.none()  # no profile, no data

        # Optional: filter by day (for dropdown in Flutter)
        day = self.request.query_params.get("day", None)
        if day:
            queryset = queryset.filter(day__iexact=day)

        # Filter by semester query param (admins only)
        semester = self.request.query_params.get("semester", None)
        if semester and user.is_staff:
            queryset = queryset.filter(semester=str(semester))

        # Always return ordered by day and time
        return queryset.order_by('day', 'start_time')

    def create(self, request, *args, **kwargs):
        """
        Allow bulk creation of multiple Routine entries at once.
        Accepts either a single JSON object or a list of objects.
        """
        is_bulk = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



    # def get_queryset(self):
    #     queryset = super().get_queryset()

    #     # Optional: Filter by day if needed
    #     day = self.request.query_params.get("day", None)
    #     if day:
    #         queryset = queryset.filter(day__iexact=day)

    #     return queryset

    

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]      #later added

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
            "address": profile.address,
            "contact_no": profile.contact_no,
            "programme": profile.programme,
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
User = get_user_model()
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    Login with email and password.
    Accepts optional device_token from Flutter.
    Saves or updates it for the logged-in user.
    Returns JWT tokens.
    """
    permission_classes = [AllowAny]
    serializer_class = EmailLoginSerializer  #Important for browsable API form

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        device_token = request.data.get('device_token')  # ADDED for device token

        # Authenticate using email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Save or update device token
        if device_token:
            # Prevent storing blank or invalid tokens
            if device_token.strip():
                DeviceToken.objects.update_or_create(
                    token=device_token.strip(),
                    defaults={'user': user}
                )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

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
    No other user (even logged in) can access someone else's profile.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    # Corrected one
    def get_object(self):
        # Always fetch the logged-in user's profile
        user = self.request.user
        try:
            return user.profile
        except Profile.DoesNotExist:
            raise NotFound("Profile not found for this user. Please register first.")

    def get(self, request, *args, **kwargs):
        """
        Override GET to return a clear error if profile is missing.
        """
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found for this user. Please register first."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(profile)
        return Response(serializer.data)


    # def get_object(self):
    #     user = self.request.user
    #     profile = getattr(user, "profile", None)
    #     if profile is None:
    #         raise NotFound("Profile not found for this user. Please register first.")
    #     return profile


    # def get(self, request, *args, **kwargs):
    #     """
    #     Override GET to return a proper error message if no profile exists.
    #     """
    #     user = request.user
    #     profile = getattr(user, "profile", None)
    #     if profile is None:
    #         return Response(
    #             {"error": "Profile not found for this user. Please register first."},
    #             status=status.HTTP_404_NOT_FOUND
    #         )

    #     serializer = self.get_serializer(profile)
    #     return Response(serializer.data)



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


# api/views.py

# class SaveFcmTokenView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Remove token from other users (if exists)
        DeviceToken.objects.filter(token=token).exclude(user=request.user).delete()

        # Create or update for current user
        DeviceToken.objects.update_or_create(token=token, defaults={"user": request.user})
        return Response({"detail": "Token saved successfully"})

# class SaveFcmTokenView(views.APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         token = request.data.get("token")
#         if not token:
#             return Response({"detail": "token required"}, status=status.HTTP_400_BAD_REQUEST)
#         DeviceToken.objects.update_or_create(token=token, defaults={"user": request.user})
#         return Response({"detail": "saved"})


# views.py
# class DeviceTokenView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        if serializer.is_valid():
            # Ensure one token per user
            token_obj, created = DeviceToken.objects.update_or_create(
                token=serializer.validated_data['token'],
                defaults={'user': request.user}
            )
            return Response({"detail": "Token saved successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        # List all tokens for the current user
        tokens = DeviceToken.objects.filter(user=request.user)
        serializer = DeviceTokenSerializer(tokens, many=True)
        return Response(serializer.data)



@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_notice_notification(request):
    """
    Send a push notification to all registered device tokens using bulk send.
    Expects JSON body:
    {
        "title": "Notification title",
        "body": "Notification body",
        "data": { "key": "value", ... }  # optional
    }
    """
    title = request.data.get("title")
    body = request.data.get("body")
    data = request.data.get("data", {})

    if not title or not body:
        return Response({"error": "Both title and body are required."}, status=400)

    # Get all device tokens
    tokens = list(DeviceToken.objects.values_list("token", flat=True))
    if not tokens:
        return Response({"message": "No device tokens found."}, status=200)

    # Firebase allows up to 500 tokens per send_multicast call
    BATCH_SIZE = 500
    success_count = 0
    failed_tokens = []

    for i in range(0, len(tokens), BATCH_SIZE):
        batch_tokens = tokens[i:i + BATCH_SIZE]

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            tokens=batch_tokens,
            data=data
        )

        response = messaging.send_multicast(message)
        success_count += response.success_count

        # Add failed tokens to list
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                failed_tokens.append(batch_tokens[idx])

    return Response({
        "message": f"Notification sent to {success_count} devices.",
        "failed_tokens": failed_tokens  # optional for debugging
    })





# @api_view(['POST'])
# @permission_classes([IsAdminUser])
# def send_notice_notification(request):
#     """
#     Send a push notification to all registered device tokens.
#     Expects JSON body:
#     {
#         "title": "Notification title",
#         "body": "Notification body",
#         "data": { "key": "value", ... }  # optional
#     }
#     """
#     title = request.data.get("title")
#     body = request.data.get("body")
#     data = request.data.get("data", {})

#     # Get all active device tokens
#     if not title or not body:
#         return Response({"error": "Both title and body are required"}, status=400)

#     tokens = DeviceToken.objects.values_list("token", flat=True)
#     success_count = 0
#     failed_tokens = []

#     for token in tokens:
#         response = send_fcm_notification(token, title, body, data)
#         if response:
#             success_count += 1
#         else:
#             failed_tokens.append(token)

#     return Response({
#         "message": f"Notification sent to {success_count} devices.",
#         "failed_tokens": failed_tokens  # optional, for debugging
#     })   









    # for token in tokens:
    #     if send_fcm_notification(token, title, body, data):
    #         success_count += 1

    # return Response({"message": f"Notification sent to {success_count} devices."})





class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Events.
    - Anyone can list or retrieve events.
    - Only admin can create, update, or delete.
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]


# class EventListCreateView(generics.ListCreateAPIView):
#     queryset = Event.objects.all()
#     serializer_class = EventSerializer

#     def get_permissions(self):
#         if self.request.method == "POST":
#             # Only admin can create events
#             return [IsAdminUser()]
#         # Everyone can GET the list
#         return [AllowAny()]


# class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Event.objects.all()
#     serializer_class = EventSerializer

#     def get_permissions(self):
#         if self.request.method in ["PUT", "PATCH", "DELETE"]:
#             # Only admin can edit or delete
#             return [IsAdminUser()]
#         # Everyone can view
#         return [AllowAny()]
