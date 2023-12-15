# Generated by Django 5.0 on 2023-12-15 08:49

import django.utils.timezone
import django_extensions.db.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("b4mad_racing_website", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profile",
            options={"get_latest_by": "modified"},
        ),
        migrations.RenameField(
            model_name="copilot",
            old_name="published_at",
            new_name="published",
        ),
        migrations.RemoveField(
            model_name="copilot",
            name="updated_at",
        ),
        migrations.AddField(
            model_name="copilot",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True, default=django.utils.timezone.now, verbose_name="created"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="copilot",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
        migrations.AddField(
            model_name="profile",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True, default=django.utils.timezone.now, verbose_name="created"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="profile",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
        ),
    ]
