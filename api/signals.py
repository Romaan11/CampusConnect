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
