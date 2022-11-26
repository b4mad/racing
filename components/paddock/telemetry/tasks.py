from celery import shared_task


# https://elkhayyat.me/shorts/django-how-to-run-celery-tasks-manually-from-shell/
@shared_task
def add(x, y):
    return x + y
