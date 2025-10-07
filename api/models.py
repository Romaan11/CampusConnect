from django.db import models
from django.contrib.auth.models import User

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
        ('Saturday', 'Saturday'),
    ]
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.day} | {self.subject} ({self.start_time} - {self.end_time})"


class Profile(models.Model):
    SHIFT_CHOICES = [
        ("morning", "Morning"),
        ("day", "Day"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    roll_no = models.CharField(max_length=50, unique=True)
    semester = models.PositiveIntegerField()
    dob = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    image = models.ImageField(upload_to="profile_images/", null=True, blank=True)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default="day")

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
#yo already existed table ho and yo model ko data fetch garera verify garxa app ma register garda
class AdmissionRecord(models.Model):
    roll_no = models.CharField(max_length=50, unique=True)
    semester = models.PositiveIntegerField()
    dob = models.DateField()
    shift = models.CharField(max_length=10, choices=Profile.SHIFT_CHOICES, default="day")

    def __str__(self):
        return f"Admission Record for {self.roll_no}"