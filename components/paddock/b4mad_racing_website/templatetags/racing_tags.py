from django import template

register = template.Library()


@register.filter
def no_jim(value):
    """Replace the name 'Jim' (which is very common in our telemetry data) with an 'unknown' string."""
    return value.replace("Jim", "👽")


@register.filter
def to_session_type(value):
    """Look up the session_type from the session_type_choices by id."""
    if value == 1:
        return "Practice"
    if value == 3:
        return "LonePractice"
    if value == 2:
        return "Race"
    if value == 4:
        return "Qualifying"
    if value == 5:
        return "Hotlap"

    return value
