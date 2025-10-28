from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event, Notice
from .utils import send_fcm_to_all


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



































# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth.models import User
# from .models import Profile


# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     # Create profile only for normal users (not admins)
#     if created and not instance.is_staff and not hasattr(instance, "profile"):
#         Profile.objects.create(user=instance)

#     # if created:
#     #     Profile.objects.create(user=instance)


# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     # Only save if profile exists
#     if hasattr(instance, "profile"):
#         instance.profile.save()
        
#     # instance.profile.save()
