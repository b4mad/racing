import logging

import b4mad_racing_website.models
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(
    b4mad_racing_website.models.copilot_enabled,
    sender=b4mad_racing_website.models.Profile,
    dispatch_uid="profile_subscription_receiver",
)
def profile_copilot_enabled(sender, **kwargs):  # pylint: disable=unused-argument
    """This signal receiver creates a new CopilotInstance if a Profile added a Copilot to its subscriptions."""
    profile = kwargs["profile"]
    copilot = kwargs["copilot"]

    logger.debug("profile_subscription_receiver called for %s/%s ", profile, profile.mqtt_drivername)
    logger.debug("profile_subscription_receiver: instance.subscriptions.all(): %s", profile.subscriptions.all())
    logger.debug("profile_subscription_receiver: kwargs: %s", kwargs)

    # let's try to find a CopilotInstance for this Profile-Copilot combination
    try:
        copilot_instance = b4mad_racing_website.models.CopilotInstance.objects.get(driver=profile, copilot_id=copilot)
        logger.debug("profile_subscription_receiver: found copilot_instance: %s", copilot_instance)
    except b4mad_racing_website.models.CopilotInstance.DoesNotExist:
        logger.debug("profile_subscription_receiver: no copilot_instance found, creating a new one")
        copilot_instance = b4mad_racing_website.models.CopilotInstance(driver=profile, copilot_id=copilot)
        if profile.mqtt_drivername != "":
            copilot_instance.mqtt_drivername = profile.mqtt_drivername
            copilot_instance.status = b4mad_racing_website.models.CopilotInstance.Status.CONFIGURED
        copilot_instance.save()
        logger.debug("profile_subscription_receiver: created copilot_instance: %s", copilot_instance)
    except KeyError:
        logger.debug("profile_subscription_receiver: no copilot_instance found, but no copilot in kwargs")
        return


@receiver(
    b4mad_racing_website.models.copilot_disabled,
    sender=b4mad_racing_website.models.Profile,
    dispatch_uid="profile_subscription_receiver",
)
def profile_copilot_disabled(sender, **kwargs):  # pylint: disable=unused-argument
    """This signal receiver creates a new CopilotInstance if a Profile added a Copilot to its subscriptions."""
    profile = kwargs["profile"]
    copilot = kwargs["copilot"]

    logger.debug("profile_subscription_receiver called for %s ", profile)
    logger.debug("profile_subscription_receiver: instance.subscriptions.all(): %s", profile.subscriptions.all())
    logger.debug("profile_subscription_receiver: kwargs: %s", kwargs)

    # let's try to find a CopilotInstance for this Profile-Copilot combination
    try:
        copilot_instance = b4mad_racing_website.models.CopilotInstance.objects.get(driver=profile, copilot_id=copilot)
        logger.debug("profile_subscription_receiver: found copilot_instance: %s, deleting!", copilot_instance)
        copilot_instance.delete()
    except b4mad_racing_website.models.CopilotInstance.DoesNotExist:
        logger.debug("profile_subscription_receiver: no copilot_instance found, do nothing")
    except KeyError:
        logger.debug("profile_subscription_receiver: no copilot_instance found, but no copilot in kwargs")
        return
