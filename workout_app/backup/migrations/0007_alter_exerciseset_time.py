# Generated by Django 4.2.2 on 2023-06-11 09:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workout_app", "0006_remove_exerciseset_exercise_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="exerciseset",
            name="time",
            field=models.CharField(blank=True, default="00:00:00:00", null=True),
        ),
    ]
