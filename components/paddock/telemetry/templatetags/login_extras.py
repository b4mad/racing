from django import template

register = template.Library()


@register.inclusion_tag("social_account_login.html")
def social_account_logins():
    return {
        "providers": [
            "discord",
            "github",
            "google",
            "microsoft",
            "reddit",
            "steam",
            "twitch",
        ]
    }
