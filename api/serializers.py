from django.contrib.auth.models import Group, User
from api.models import Notice, Routine, Profile, AdmissionRecord
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta, datetime


# -------------------- PROFILE --------------------
class ProfileSerializer(serializers.ModelSerializer):
    # dob = serializers.CharField()
    # shift = serializers.CharField()

    class Meta:
        model = Profile
        fields = ['name', 'email', 'roll_no', 'semester', 'dob', 'address', 'image', 'shift']

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
    profile = ProfileSerializer(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password2', 'profile']

    def validate_email(self, value):
        # # Prevent fake/anime-looking emails (simple regex for real names)
        # import re
        # name_part = value.split('@')[0]
        # if not re.match(r"^[A-Za-z]+(\.[A-Za-z]+)*$", name_part):
        #     raise serializers.ValidationError(
        #         "Please use a real name email (e.g., firstname.lastname@gmail.com)."
        #     )

        # Check if user email already exists        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        
        # Check if this email exists in AdmissionRecord
        if not AdmissionRecord.objects.filter(email=value).exists():
            raise serializers.ValidationError("No admission record found for this email.")
        return value


    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
    

    def create(self, validated_data):
        # from api.models import AdmissionRecord  # import inside for safety

        profile_data = validated_data.pop('profile')
        email = validated_data['email']
        password = validated_data['password']

        # # 1. Verify admission data before registration
        # roll_no = profile_data.get('roll_no')
        # dob = profile_data.get('dob')
        # semester = profile_data.get('semester')
        # shift = profile_data.get('shift').lower()

        # Fetch admission record for validation
        try:
            admission = AdmissionRecord.objects.get(email = email)
        except AdmissionRecord.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "No admission record found for this email."}
            )

        # Check if other details match
        errors = {}
        # if admission.dob != dob:
        #     errors["dob"] = "Date of birth does not match our records."
        if admission.name != profile_data.get('name'):
            errors["name"] = "Name does not match Admission Records."
        if admission.roll_no != profile_data.get('roll_no'):
            errors["roll_no"] = "Roll number does not match Admission Records."            
        if str(admission.semester) != str(profile_data.get('semester')):
            errors["semester"] = "Semester does not match Admission Record."
        if admission.dob.strip() != profile_data.get('dob').strip():
            errors["dob"] = "Date of Birth does not match Admission Record."
        if admission.address.strip().lower() != profile_data.get('address').strip().lower():
            errors["address"] = "Address does not match Admission Record."
        if admission.shift.lower() != profile_data.get('shift').lower():
            errors["shift"] = "Shift must be 'morning' or 'day' (matching Admission Record)."

        # # Convert provided DOB to comparable date
        # try:
        #     year, month, day = map(int, dob_text.split('/'))
        #     dob_date = datetime(year, month, day).date()
        # except Exception:
        #     raise serializers.ValidationError({"dob": "Invalid DOB format (use YYYY/MM/DD)."})
        # if admission.dob != dob_date:
        #     errors["dob"] = "DOB does not match our records."


        if errors:
            raise serializers.ValidationError(errors)


        # 2. Create user
        user = User.objects.create_user(
            username=profile_data.get('name'),
            email=email,
            password=password
        )
        user.is_staff = False  # not admin
        user.save()

        # Create verified profile
        Profile.objects.create(user=user, **profile_data)
        
        return user

    # def create(self, validated_data):
    #     from api.models import AdmissionRecord  # import inside for safety

    #     profile_data = validated_data.pop('profile')
    #     email = validated_data['email']
    #     password = validated_data['password']

    #     # Extract username from email
    #     base_username = email.split("@")[0]
    #     username = base_username
    #     counter = 1
    #     while User.objects.filter(username=username).exists():
    #         username = f"{base_username}{counter}"
    #         counter += 1

    #     # Create user
    #     user = User.objects.create_user(
    #         username=username,
    #         email=email,
    #         password=password
    #     )
    #     user.is_staff = False
    #     user.save()

    #     # Create profile for this user
    #     Profile.objects.create(user=user, **profile_data)

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
