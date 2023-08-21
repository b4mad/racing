# Generated by Django 4.2.3 on 2023-08-21 15:07

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("telemetry", "0014_carclass_car_car_class"),
    ]

    operations = [
        migrations.CreateModel(
            name="Landmark",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("start", models.IntegerField(null=True)),
                ("end", models.IntegerField(null=True)),
                ("is_overtaking_spot", models.BooleanField(null=True)),
                (
                    "kind",
                    models.CharField(
                        choices=[("misc", "Misc"), ("segment", "Segment"), ("turn", "Turn")],
                        default="misc",
                        max_length=64,
                    ),
                ),
                (
                    "track",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="landmarks", to="telemetry.track"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
