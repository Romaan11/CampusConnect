from django.contrib.auth.models import Group, User
from api.models import Notice, Routine, Profile, AdmissionRecord, Event, DeviceToken
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta, datetime

from django.db import transaction
from rest_framework.exceptions import ValidationError


# -------------------- PROFILE --------------------
class ProfileSerializer(serializers.ModelSerializer):
    # dob = serializers.CharField()
    # shift = serializers.CharField()

    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'roll_no', 'semester', 'dob', 'address', 'image', 'shift', 'programme', 'contact_no']    # 'email', 'name',


    def validate(self, attrs):
        # Only allow 'image' to be updated
        forbidden_fields = set(attrs.keys()) - {'image'}
        if forbidden_fields:
            raise ValidationError(
                {field: "This field cannot be updated." for field in forbidden_fields}
            )
        return attrs
        # read_only_fields = [
        #     'first_name', 'last_name', 'roll_no', 'semester',
        #     'dob', 'address', 'shift', 'programme', 'contact_no'
        # ]  # make all fields read-only except image



 

    # def validate_dob(self, value):
    #     """Validate DOB format: YYYY/MM/DD (BS)."""
    #     import re
    #     pattern = r"^\d{4}/\d{2}/\d{2}$"
    #     if not re.match(pattern, value):
    #         raise serializers.ValidationError("DOB must be in YYYY/MM/DD format (Bikram Sambat).")

    #     # Convert BS to AD if you want (optional) — currently it just stores the same format
    #     try:
    #         parts = value.split('/')
    #         datetime(int(parts[0]), int(parts[1]), int(parts[2]))  # validate structure
    #     except Exception:
    #         raise serializers.ValidationError("Invalid date format.")
    #     return value

    # def validate_shift(self, value):
    #     """Ensure shift is either morning or day (case-insensitive)."""
    #     shift_value = value.strip().lower()
    #     if shift_value not in ['morning', 'day']:
    #         raise serializers.ValidationError("Shift must be either 'morning' or 'day'.")
    #     return shift_value


# -------------------- USERS --------------------
class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)     

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'groups',
            'first_name', 'last_name', 'is_staff', 'profile'
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        user = super().update(instance, validated_data)

        if profile_data:
            Profile.objects.update_or_create(user=user, defaults=profile_data)

        return user


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Used by admin to create users manually.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'is_staff')

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            is_staff=validated_data.get('is_staff', False)
        )




# -------------------- EMAIL LOGIN --------------------
User = get_user_model()

class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user with this email found.")

            user = authenticate(username=user_obj.username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")

            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Email and password are required.")


# -------------------- GROUPS --------------------
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


# -------------------- NOTICES --------------------
class NoticeSerializer(serializers.ModelSerializer):
    featured_image = serializers.ImageField(use_url=True)

    class Meta:
        model = Notice
        fields = [
            'id',
            'title',
            'content',
            'featured_image',
            'author',
            'published_at',
        ]
        extra_kwargs = {
            "author": {"read_only": True},
            "published_at": {"read_only": True},
        }

    def validate(self, data):
        data["author"] = self.context["request"].user
        return data


# -------------------- ROUTINES --------------------
class RoutineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Routine
        fields = '__all__'


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_new_password = serializers.CharField(write_only=True, required=True)


# Admin registers user and creates admission record and user and profile are created at the same time
class AdmissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionRecord
        fields = [
            "first_name",
            "last_name",
            "email",
            "roll_no",
            "semester",
            "dob",
            "address",
            "shift",
            "programme",
            "contact_no",
            "image",
        ]

    def validate_email(self, value):
        if value and AdmissionRecord.objects.filter(email=value).exists():
            raise serializers.ValidationError("An admission record with this email already exists.")
        return value

    def validate_roll_no(self, value):
        if AdmissionRecord.objects.filter(roll_no=value).exists():
            raise serializers.ValidationError("An admission record with this roll number already exists.")
        return value










# -------------------- REGISTER --------------------
# class RegisterSerializer(serializers.ModelSerializer):
#     """
#     Student self-registration with email + password + profile info.
#     Always creates non-admin users.
#     Profile info verified with AdmissionRecord before creation.
#     """
#     password = serializers.CharField(write_only=True, validators=[validate_password])
#     password2 = serializers.CharField(write_only=True)

#  ### CHANGED / ADDED — directly accept profile fields (no nested object)
#     first_name = serializers.CharField()
#     last_name = serializers.CharField()
#     roll_no = serializers.CharField()
#     semester = serializers.CharField()
#     dob = serializers.CharField()
#     address = serializers.CharField()
#     shift = serializers.CharField()
#     programme = serializers.CharField()     
#     contact_no = serializers.CharField()
#     image = serializers.ImageField(required=False, allow_null=True)

#     class Meta:
#         model = User
#         fields = [
#             'email', 'password', 'password2',
#             'first_name', 'last_name', 'roll_no', 'semester',
#             'dob', 'address', 'shift', 'programme', 'contact_no', 'image'
#         ]

#     def validate_email(self, value):
#         if User.objects.filter(email=value).exists():
#             raise serializers.ValidationError("This email is already registered.")

#         if not AdmissionRecord.objects.filter(email=value).exists():
#             raise serializers.ValidationError("No admission record found for this email.")
#         return value

#     def validate(self, attrs):
#         if attrs['password'] != attrs['password2']:
#             raise serializers.ValidationError({"password": "Passwords do not match."})

#         required = ['first_name', 'last_name', 'roll_no', 'semester', 'dob', 'address', 'shift', 'programme', 'contact_no']
#         missing = [f for f in required if not attrs.get(f)]
#         if missing:
#             raise serializers.ValidationError({"profile": f"Missing fields: {', '.join(missing)}"})
        
#         # Validate semester is int
#         try:
#             int(str(attrs.get('semester')).strip())
#         except Exception:
#             raise serializers.ValidationError({"semester": "Semester must be an integer."})

#         return attrs

#     def create(self, validated_data):
#         email = validated_data['email']
#         password = validated_data['password']
#         validated_data.pop('password2')

#         ### CHANGED — profile data extracted directly (no nested key)
#         profile_data = {
#             'first_name': validated_data.pop('first_name'),
#             'last_name': validated_data.pop('last_name'),
#             'roll_no': validated_data.pop('roll_no'),
#             'semester': validated_data.pop('semester'),
#             'dob': validated_data.pop('dob'),
#             'address': validated_data.pop('address'),
#             'shift': validated_data.pop('shift'),
#             'programme': validated_data.pop('programme'),
#             'contact_no': validated_data.pop('contact_no'),
#             'image': validated_data.pop('image', None),
#         }

#         # Fetch admission record for validation
#         try:
#             admission = AdmissionRecord.objects.get(email=email)
#         except AdmissionRecord.DoesNotExist:
#             raise ValidationError({"email": "No admission record found for this email."})

#         # Validate against admission record
#         errors = {}
#         if admission.first_name.strip().lower() != profile_data['first_name'].strip().lower():
#             errors["first_name"] = "First name does not match Admission Record."
#         if admission.last_name.strip().lower() != profile_data['last_name'].strip().lower():
#             errors["last_name"] = "Last name does not match Admission Record."
#         if admission.roll_no != profile_data.get('roll_no'):
#             errors["roll_no"] = "Roll number does not match Admission Record."

#         try:
#             provided_sem = int(str(profile_data.get('semester')).strip())
#         except Exception:
#             provided_sem = None
#         if provided_sem is None or int(admission.semester) != provided_sem:
#             errors["semester"] = "Semester does not match Admission Record."

#         if admission.dob.strip() != profile_data.get('dob').strip():
#             errors["dob"] = "Date of Birth does not match Admission Record."
#         if admission.address.strip().lower() != profile_data.get('address').strip().lower():
#             errors["address"] = "Address does not match Admission Record."
#         if admission.shift.strip().lower() != profile_data.get('shift').strip().lower():
#             errors["shift"] = "Shift must match Admission Record ('morning' or 'day')."
#         if admission.programme.strip().lower() != profile_data['programme'].strip().lower():
#             errors["programme"] = "Programme does not match Admission Record."
#         if admission.contact_no.strip() != profile_data['contact_no'].strip():
#             errors["contact_no"] = "Contact number does not match Admission Record."

#         if errors:
#             raise ValidationError(errors)

#         ### CHANGED — create username = "FirstName LastName" with space
#         base_username = f"{profile_data['first_name']} {profile_data['last_name']}".strip()
#         username = base_username
#         counter = 1
#         while User.objects.filter(username=username).exists():
#             username = f"{base_username} {counter}"
#             counter += 1

#         with transaction.atomic():
#             user = User.objects.create_user(
#                 username=username,
#                 email=email,
#                 password=password,
#                 first_name=profile_data['first_name'],
#                 last_name=profile_data['last_name']
#             )
#             user.is_staff = False
#             user.save()

#             Profile.objects.create(
#                 user=user,
#                 first_name=profile_data['first_name'],
#                 last_name=profile_data['last_name'],
#                 name=f"{profile_data['first_name']} {profile_data['last_name']}",
#                 email=email,
#                 roll_no=profile_data['roll_no'],
#                 semester=int(profile_data['semester']),
#                 dob=profile_data['dob'],
#                 address=profile_data['address'],
#                 image=profile_data.get('image', None),
#                 shift=profile_data['shift'],
#                 programme=profile_data['programme'],
#                 contact_no=profile_data['contact_no'],
#             )

#         return user


 





