#!/usr/bin/env python

import subprocess
import time

import django
from flask import Flask, make_response

django.setup()

from allauth.socialaccount.models import SocialAccount  # noqa: E402
from apscheduler.schedulers.background import BackgroundScheduler  # noqa: E402

from telemetry.models import Coach, Driver  # noqa: E402

app = Flask(__name__)
scheduler = BackgroundScheduler()

# set up default values for metrics
drivers = -1
coaches = -1
social_accounts = -1


@app.route("/")
def main():
    return "ok"


@app.route("/metrics")
def metrics():
    response = make_response(generate_metrics(), 200)
    response.mimetype = "text/plain"
    return response


def generate_metrics():
    global drivers
    global coaches
    global social_accounts

    try:
        git_version = subprocess.check_output(["git", "describe"]).strip().decode("utf-8")
    except subprocess.CalledProcessError:
        git_version = "v0.0.0+error_in_git_describe"

    return (
        "# HELP paddock_drivers_total The total number of drivers\n"
        "# TYPE paddock_drivers_total gauge\n"
        f"paddock_drivers_total {drivers}\n"
        "# HELP paddock_coaches_total The total number of coaches\n"
        "# TYPE paddock_coaches_total gauge\n"
        f"paddock_coaches_total {coaches}\n"
        "# HELP paddock_social_accounts_total The total number of social accounts\n"
        "# TYPE paddock_social_accounts_total gauge\n"
        f"paddock_social_accounts_total {social_accounts}\n"
        "# HELP paddock_info The version of the paddock\n"
        "# TYPE paddock_info gauge\n"
        f'paddock_info{{version="{git_version}"}} 1\n'
    )


def update_paddock_metrics():
    global drivers
    global coaches
    global social_accounts

    drivers = Driver.objects.count()
    coaches = Coach.objects.count()
    social_accounts = SocialAccount.objects.count()

    time.sleep(5)


if __name__ == "__main__":
    metric_init_job = scheduler.add_job(update_paddock_metrics)
    metric_update_job = scheduler.add_job(update_paddock_metrics, "interval", minutes=5)

    scheduler.start()
    app.run("0.0.0.0", 8081)
