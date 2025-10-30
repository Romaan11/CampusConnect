from django.db import models
from django.contrib.auth.models import User

from django.utils import timezone
from datetime import timedelta


# # Added new DeviceToken model

class DeviceToken(models.Model):
    user = models.ForeignKey(
        User, 
        related_name='device_tokens', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="The user this device belongs to. Can be null if not logged in yet."
    )
    token = models.CharField(
        max_length=255, 
        unique=True,
        help_text="The Firebase Cloud Messaging device token."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
        ordering = ['-last_seen']  # optional, newest active devices first

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.token[:20]}..."

    def update_last_seen(self):
        """Call this when the user opens the app to update last_seen timestamp."""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])

# class DeviceToken(models.Model):
#     user = models.ForeignKey(User, related_name='device_tokens', on_delete=models.CASCADE, null=True, blank=True)
#     token = models.CharField(max_length=255, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_seen = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user} - {self.token[:20]}"


class Notice(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    featured_image = models.ImageField(upload_to="notice_images/%Y/%m/%d/", null=True, blank=False)
    author = models.ForeignKey("auth.User", on_delete = models.CASCADE)
    published_at = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-published_at']


class Routine(models.Model):
    DAYS_OF_WEEK = [
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        # ('Saturday', 'Saturday'),
    ]

    SEMESTER_CHOICES = [
        ('1', '1st Semester'),
        ('2', '2nd Semester'),
        ('3', '3rd Semester'),
        ('4', '4th Semester'),
        ('5', '5th Semester'),
        ('6', '6th Semester'),
        ('7', '7th Semester'),
        ('8', '8th Semester'),
    ]

    semester = models.CharField(max_length=2, choices=SEMESTER_CHOICES)
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    subject = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.semester} | {self.day} | {self.subject} ({self.start_time} - {self.end_time})"


class Profile(models.Model):
    # SHIFT_CHOICES = [
    #     ("morning", "Morning"),
    #     ("day", "Day"),
    # ]

    user = models.OneToOneField(User, on_delete=models.CASCADE) #, related_name="profile"
    first_name = models.CharField(max_length=100, default="")
    last_name = models.CharField(max_length=100, default="")
    name = models.CharField(max_length=255)  # Combined name for display
    email = models.EmailField(unique=True, blank=True, null=True)
    roll_no = models.CharField(max_length=50, unique=True)
    semester = models.IntegerField()
    # keep dob as text field so user types BS date (YYYY/MM/DD)
    dob = models.CharField(max_length=20, help_text="Format: YYYY/MM/DD (AD)") 
    # dob = models.CharField(max_length=12, null=True, blank=True)
    # dob = models.DateField(null=True, blank=True)
    address = models.CharField(blank=True, max_length=255)
    image = models.ImageField(upload_to="profile_images/", null=True, blank=True)
    shift = models.CharField(max_length=10, help_text="Type either 'morning' or 'day' manually" ) #choices=SHIFT_CHOICES,default="day"
    programme = models.CharField(max_length=100, default="")  
    contact_no = models.CharField(max_length=15, default="")  

    def __str__(self):
        return f"{self.user.username}'s Profile"

# This table stores admission data (used for verification)    
#yo already existed table ho and yo model ko data fetch garera verify garxa app ma register garda
class AdmissionRecord(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100, default="")
    last_name = models.CharField(max_length=100, default="")
    # email = models.EmailField(unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    roll_no = models.CharField(max_length=50, unique=True)
    semester = models.PositiveIntegerField()
    dob = models.CharField(max_length=20, help_text="Format: YYYY/MM/DD (AD)")  # AD format (YYYY/MM/DD)
    address = models.TextField()
    shift = models.CharField(max_length=10) #choices=Profile.SHIFT_CHOICES,  default="day"
    programme = models.CharField(max_length=100, default="")  
    contact_no = models.CharField(max_length=15, default="")
    image = models.ImageField(upload_to='admission_images/', null=True, blank=True)

    def __str__(self):
        return f"Admission Record for {self.first_name} {self.last_name} ({self.roll_no})"
        # return f"Admission Record: {self.roll_no} - {self.name}"  


class Event(models.Model):
    event_title = models.CharField(max_length=200)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    event_detail = models.TextField()
    location = models.CharField(max_length=255)
    image = models.ImageField(upload_to="events/")
    
    def __str__(self):
        return self.event_title



class PasswordResetCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reset_code')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.username} - {self.code}"