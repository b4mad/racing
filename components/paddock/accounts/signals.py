from b4mad_racing_website.models import Profile
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def create_profile(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=get_user_model())
def save_profile(sender, instance, **kwargs):  # pylint: disable=unused-argument
    instance.profile.save()
