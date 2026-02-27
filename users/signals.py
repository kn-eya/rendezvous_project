from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """
    Ensure every user has a Profile.
    - Creates a default client profile on user creation.
    - If a user somehow lost their profile, recreate it on save.
    """
    if created:
        Profile.objects.create(user=instance, role='client')
        return

    # If profile was deleted manually, recreate it to keep navbar safe
    if not hasattr(instance, "profile"):
        Profile.objects.create(user=instance, role='client')
