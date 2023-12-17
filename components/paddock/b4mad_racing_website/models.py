import logging
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.dispatch import Signal
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

copilot_enabled = Signal()
copilot_disabled = Signal()

logger = logging.getLogger(__name__)


class Copilot(TimeStampedModel):
    name = models.CharField(max_length=127)
    description = models.CharField(max_length=255)
    published = models.DateTimeField("publishing date")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return str(self.name)


# pylint: disable=no-member
class Profile(TimeStampedModel):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    slug = models.SlugField(default=None)
    mqtt_drivername = models.CharField(max_length=64, default="", null=True, blank=True)
    initial_transport_test_passed = models.BooleanField(default=False)
    publicly_visible = models.BooleanField(default=True)
    newsletter_allowed = models.BooleanField(default=True)

    subscriptions = models.ManyToManyField(Copilot, blank=True)

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return reverse("profile", kwargs={"slug": self.slug})

    def is_public(self):
        return self.publicly_visible

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.user.username)
        return super().save(*args, **kwargs)

    def subscribe_copilot(self, copilot: Copilot):
        logger.debug("subscribe_copilot called for %s: %s ", self, copilot)
        self.subscriptions.add(copilot)
        copilot_enabled.send(sender=self.__class__, profile=self, copilot=copilot)
        self.save()

    def unsubscribe_copilot(self, copilot: Copilot):
        logger.debug("unsubscribe_copilot called: user=%s: copilot=%s ", self, copilot)
        self.subscriptions.remove(copilot)
        copilot_disabled.send(sender=self.__class__, profile=self, copilot=copilot)
        self.save()


class CopilotInstance(TimeStampedModel):
    """This model represents a instance of a Copilot belonging to a Driver."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(Profile, on_delete=models.CASCADE, default=None, null=True, blank=True)
    copilot = models.ForeignKey(Copilot, on_delete=models.CASCADE, default=None, null=True, blank=True)

    # pylint: disable=too-many-ancestors
    class Status(models.TextChoices):
        ENABLED = "ENABLED", _("Enabled")
        DISABLED = "DISABLED", _("Disabled")
        MISCONFIGURED = "MISCONFIGURED", _("Misconfigured")
        CONFIGURED = "CONFIGURED", _("Configured")
        RUNNING = "RUNNING", _("Running")
        STOPPED = "STOPPED", _("Stopped")
        ERROR = "ERROR", _("Error")

    status = models.CharField(
        max_length=13,
        choices=Status.choices,
        default=Status.MISCONFIGURED,  # we assume, that the mqtt_drivername is not set
    )

    def enabled(self):
        return self.status == CopilotInstance.Status.ENABLED
