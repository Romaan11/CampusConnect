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


# -------------------- REGISTER --------------------
class RegisterSerializer(serializers.ModelSerializer):
    """
    Student self-registration with email + password + profile info.
    Always creates non-admin users.
    Profile info verified with AdmissionRecord before creation.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

 ### CHANGED / ADDED — directly accept profile fields (no nested object)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    roll_no = serializers.CharField()
    semester = serializers.CharField()
    dob = serializers.CharField()
    address = serializers.CharField()
    shift = serializers.CharField()
    programme = serializers.CharField()     
    contact_no = serializers.CharField()
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password2',
            'first_name', 'last_name', 'roll_no', 'semester',
            'dob', 'address', 'shift', 'programme', 'contact_no', 'image'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")

        if not AdmissionRecord.objects.filter(email=value).exists():
            raise serializers.ValidationError("No admission record found for this email.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        required = ['first_name', 'last_name', 'roll_no', 'semester', 'dob', 'address', 'shift', 'programme', 'contact_no']
        missing = [f for f in required if not attrs.get(f)]
        if missing:
            raise serializers.ValidationError({"profile": f"Missing fields: {', '.join(missing)}"})
        
        # Validate semester is int
        try:
            int(str(attrs.get('semester')).strip())
        except Exception:
            raise serializers.ValidationError({"semester": "Semester must be an integer."})

        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        validated_data.pop('password2')

        ### CHANGED — profile data extracted directly (no nested key)
        profile_data = {
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'roll_no': validated_data.pop('roll_no'),
            'semester': validated_data.pop('semester'),
            'dob': validated_data.pop('dob'),
            'address': validated_data.pop('address'),
            'shift': validated_data.pop('shift'),
            'programme': validated_data.pop('programme'),
            'contact_no': validated_data.pop('contact_no'),
            'image': validated_data.pop('image', None),
        }

        # Fetch admission record for validation
        try:
            admission = AdmissionRecord.objects.get(email=email)
        except AdmissionRecord.DoesNotExist:
            raise ValidationError({"email": "No admission record found for this email."})

        # Validate against admission record
        errors = {}
        if admission.first_name.strip().lower() != profile_data['first_name'].strip().lower():
            errors["first_name"] = "First name does not match Admission Record."
        if admission.last_name.strip().lower() != profile_data['last_name'].strip().lower():
            errors["last_name"] = "Last name does not match Admission Record."
        if admission.roll_no != profile_data.get('roll_no'):
            errors["roll_no"] = "Roll number does not match Admission Record."

        try:
            provided_sem = int(str(profile_data.get('semester')).strip())
        except Exception:
            provided_sem = None
        if provided_sem is None or int(admission.semester) != provided_sem:
            errors["semester"] = "Semester does not match Admission Record."

        if admission.dob.strip() != profile_data.get('dob').strip():
            errors["dob"] = "Date of Birth does not match Admission Record."
        if admission.address.strip().lower() != profile_data.get('address').strip().lower():
            errors["address"] = "Address does not match Admission Record."
        if admission.shift.strip().lower() != profile_data.get('shift').strip().lower():
            errors["shift"] = "Shift must match Admission Record ('morning' or 'day')."
        if admission.programme.strip().lower() != profile_data['programme'].strip().lower():
            errors["programme"] = "Programme does not match Admission Record."
        if admission.contact_no.strip() != profile_data['contact_no'].strip():
            errors["contact_no"] = "Contact number does not match Admission Record."

        if errors:
            raise ValidationError(errors)

        ### CHANGED — create username = "FirstName LastName" with space
        base_username = f"{profile_data['first_name']} {profile_data['last_name']}".strip()
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username} {counter}"
            counter += 1

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=profile_data['first_name'],
                last_name=profile_data['last_name']
            )
            user.is_staff = False
            user.save()

            Profile.objects.create(
                user=user,
                first_name=profile_data['first_name'],
                last_name=profile_data['last_name'],
                name=f"{profile_data['first_name']} {profile_data['last_name']}",
                email=email,
                roll_no=profile_data['roll_no'],
                semester=int(profile_data['semester']),
                dob=profile_data['dob'],
                address=profile_data['address'],
                image=profile_data.get('image', None),
                shift=profile_data['shift'],
                programme=profile_data['programme'],
                contact_no=profile_data['contact_no'],
            )

        return user


    # profile = ProfileSerializer(write_only=True)
        


    # class Meta:
    #     model = User
    #     fields = ['email', 'password', 'password2', 'profile']

    # def validate_email(self, value):
    #     # Check if user email already exists        
    #     if User.objects.filter(email=value).exists():
    #         raise serializers.ValidationError("This email is already registered.")
        
    #     # Check if this email exists in AdmissionRecord
    #     if not AdmissionRecord.objects.filter(email=value).exists():
    #         raise serializers.ValidationError("No admission record found for this email.")
    #     return value


    # def validate(self, attrs):
    #     # Ensure profile block exists and required fields are present
    #     profile_data = attrs.get('profile')
    #     if not profile_data:
    #         raise serializers.ValidationError({"profile": "Profile data is required."})

    #     # Check password match
    #     if attrs['password'] != attrs['password2']:
    #         raise serializers.ValidationError({"password": "Passwords do not match."})
    #     # return attrs


    #     required = ['first_name', 'last_name', 'roll_no', 'semester', 'dob', 'address', 'shift']
    #     missing = [f for f in required if not profile_data.get(f)]
    #     # missing = [f for f in required if not profile_data.get(f) and profile_data.get(f) != 0]
    #     if missing:
    #         raise serializers.ValidationError({"profile": f"Missing profile fields: {', '.join(missing)}"})

    #     # Validate semester can be coerced to int
    #     sem = profile_data.get('semester')
    #     try:
    #         # allow strings like "7"
    #         int(str(sem).strip())
    #     except Exception:
    #         raise serializers.ValidationError({"profile": {"semester": "Semester must be an integer."}})

    #     return attrs
    

    # def create(self, validated_data):
    #     # from api.models import AdmissionRecord  # import inside for safety

    #     profile_data = validated_data.pop('profile')
    #     email = validated_data['email']
    #     password = validated_data['password']

    #     # # 1. Verify admission data before registration
    #     # roll_no = profile_data.get('roll_no')
    #     # dob = profile_data.get('dob')
    #     # semester = profile_data.get('semester')
    #     # shift = profile_data.get('shift').lower()

    #     # Fetch admission record for validation
    #     try:
    #         admission = AdmissionRecord.objects.get(email = email)
    #     except AdmissionRecord.DoesNotExist:
    #         raise serializers.ValidationError(
    #             {"email": "No admission record found for this email."}
    #         )

    #     # Check if entered profile info with AdmissionRecord
    #     errors = {}
    #     # if admission.dob != dob:
    #     #     errors["dob"] = "Date of birth does not match our records."
    #     # if admission.name != profile_data.get('name'):
    #     #     errors["name"] = "Name does not match Admission Records."
    #     if admission.first_name.strip().lower() != profile_data['first_name'].strip().lower():
    #         errors["first_name"] = "First name does not match Admission Record."
    #     if admission.last_name.strip().lower() != profile_data['last_name'].strip().lower():
    #         errors["last_name"] = "Last name does not match Admission Record."
    #     if admission.roll_no != profile_data.get('roll_no'):
    #         errors["roll_no"] = "Roll number does not match Admission Records."    

    #     # Normalize semester comparison
    #     try:
    #         provided_sem = int(str(profile_data.get('semester')).strip())
    #     except Exception:
    #         provided_sem = None
    #     if provided_sem is None or int(admission.semester) != provided_sem:
    #         errors["semester"] = "Semester does not match Admission Record."
    #     # if str(admission.semester) != str(profile_data.get('semester')):
    #     #     errors["semester"] = "Semester does not match Admission Record."
    #     if admission.dob.strip() != profile_data.get('dob').strip():
    #         errors["dob"] = "Date of Birth does not match Admission Record."
    #     if admission.address.strip().lower() != profile_data.get('address').strip().lower():
    #         errors["address"] = "Address does not match Admission Record."
    #     # if admission.shift.lower() != profile_data.get('shift').lower():
    #     if admission.shift.strip().lower() != profile_data.get('shift').strip().lower():
    #         errors["shift"] = "Shift must be 'morning' or 'day' (matching Admission Record)."

    #     if errors:
    #         # raise serializers.ValidationError(errors)
    #         raise ValidationError(errors)


    #     # ensure username uniqueness (derive from name, fallback to email part)
    #     # base_username = profile_data.get('name') or email.split("@")[0]

    #     # Combine first + last name for username [USERNAME GENERATION (space added here)]
    #     base_username = f"{profile_data['first_name']} {profile_data['last_name']}".strip().lower()
    #     username = base_username
    #     counter = 1
    #     while User.objects.filter(username=username).exists():
    #         username = f"{base_username} {counter}"
    #         counter += 1

    #     # Convert semester to int for Profile creation (guaranteed by prior checks)
    #     semester_int = int(str(profile_data.get('semester')).strip())

    #     # # Debug print
    #     # print("PROFILE DATA:", profile_data)
    #     # print("SEMESTER VALUE BEFORE SAVE:", repr(profile_data.get('semester')))

    #     # Create both user and profile atomically to avoid partial creation
    #     with transaction.atomic():
    #         user = User.objects.create_user(
    #             username=username,
    #             email=email,
    #             password=password,
    #             first_name=profile_data['first_name'],
    #             last_name=profile_data['last_name']
    #         )
    #         user.is_staff = False
    #         user.save()

    #         # Create verified profile
    #         Profile.objects.create(
    #             user=user,
    #             first_name=profile_data['first_name'],
    #             last_name=profile_data['last_name'],
    #             name=f"{profile_data['first_name']} {profile_data['last_name']}",   # auto-generated full name
    #             # name=profile_data.get('name'),
    #             roll_no=profile_data.get('roll_no'),
    #             semester=semester_int,
    #             dob=profile_data.get('dob'),
    #             address=profile_data.get('address'),
    #             image=profile_data.get('image', None),
    #             shift=profile_data.get('shift')
    #         )

    #     return user




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


# class DeviceTokenSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DeviceToken
#         fields = '__all__'


# class DeviceTokenSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DeviceToken
#         fields = ['id', 'token', 'user', 'created_at']
#         read_only_fields = ['id', 'user', 'created_at']