# Generated by Django 4.2.3 on 2023-08-28 16:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("telemetry", "0017_trackguide_trackguidenote"),
    ]

    operations = [
        migrations.AddField(
            model_name="trackguidenote",
            name="at",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="coach",
            name="mode",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("track_guide", "Track Guide"),
                    ("debug", "Debug"),
                    ("only_brake", "Only Brakepoints"),
                    ("only_brake_debug", "Only Brakepoints (Debug))"),
                ],
                default="default",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="fastlap",
            name="car",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="fast_laps", to="telemetry.car"
            ),
        ),
        migrations.AlterField(
            model_name="fastlap",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="fast_laps", to="telemetry.game"
            ),
        ),
        migrations.AlterField(
            model_name="fastlap",
            name="track",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="fast_laps", to="telemetry.track"
            ),
        ),
    ]