from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Event, Notice, AdmissionRecord, Profile
from .utils import send_fcm_to_all
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings



@receiver(post_save, sender=Event)
def notify_on_event_create(sender, instance, created, **kwargs):
    """
    Sends a push notification to all devices when a new Event is created.
    """
    if created:
        send_fcm_to_all(
            title=f"New Event: {instance.event_title}",
            body=f"{instance.event_detail[:100]}...",  # show first 100 chars of detail
            data={"event_id": str(instance.id)}
        )


@receiver(post_save, sender=Notice)
def notify_on_notice_create(sender, instance, created, **kwargs):
    """
    Sends a push notification to all devices when a new Notice is created.
    """
    if created:
        send_fcm_to_all(
            title=f"New Notice: {instance.title}",
            body=f"{instance.body[:100]}..." if hasattr(instance, "body") and instance.body else "Tap to view details.",
            data={"notice_id": str(instance.id)}
        )






# for automatically creating profile and user when record is entered in admissionrecord
# and sends email and temporary password to user's email
@receiver(post_save, sender=AdmissionRecord)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    When a new AdmissionRecord is created:
    - Create a corresponding User and Profile
    - Send email with email + temporary password
    """

    # Create a clean username (capitalized, with space)
    username = f"{instance.first_name.capitalize()} {instance.last_name.capitalize()}"

    # Check if a user already exists with this email
    user = User.objects.filter(email=instance.email).first()

    if not user:
        # Generate random temporary password
        random_password = get_random_string(length=8)

        # Create new user
        user = User.objects.create_user(
            username=username,
            email=instance.email,
            first_name=instance.first_name.capitalize(),
            last_name=instance.last_name.capitalize(),
            password=random_password,
            is_staff=False,
        )

        print(f"New user created: {user.username} | Password: {random_password}")

        # Send account details via email
        subject = "Your CampusConnect Account Credentials"
        message = (
            f"Hello {instance.first_name.capitalize()},\n\n"
            f"Your CampusConnect account has been created successfully.\n\n"
            f"Email: {instance.email}\n"
            f"Password: {random_password}\n\n"
            f"Please log in and change your password after your first login.\n\n"
            f"Thank you,\nCampusConnect Admin Team"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=False,
            )
            print(f"Password email sent to {instance.email}")
        except Exception as e:
            print(f"Failed to send email to {instance.email}: {e}")

    else:
        # Update existing user details
        user.first_name = instance.first_name.capitalize()
        user.last_name = instance.last_name.capitalize()
        user.email = instance.email
        user.username = username
        user.save(update_fields=["first_name", "last_name", "email", "username"])
        print(f"Updated existing user: {user.username}")

    # Sync Profile
    Profile.objects.update_or_create(
        user=user,
        defaults={
            "first_name": instance.first_name.capitalize(),
            "last_name": instance.last_name.capitalize(),
            "name": username,
            "email": instance.email,
            "roll_no": instance.roll_no,
            "semester": instance.semester,
            "dob": instance.dob,
            "address": instance.address,
            "shift": instance.shift,
            "programme": instance.programme,
            "contact_no": instance.contact_no,
            "image": instance.image,
        },
    )
    print(f"Profile synced for: {user.username}")


@receiver(post_delete, sender=AdmissionRecord)
def delete_related_user_profile(sender, instance, **kwargs):
    """
    Deletes User & Profile when AdmissionRecord is deleted.
    """
    try:
        user = User.objects.get(email=instance.email)
        user.delete()
        print(f"Deleted user and profile for {instance.email}")
    except User.DoesNotExist:
        pass
