import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Identity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(
                    choices=[
                        ("email", "Email"),
                        ("phone", "Phone"),
                        ("google", "Google"),
                        ("apple", "Apple"),
                    ],
                    max_length=50,
                )),
                ("identifier", models.CharField(max_length=255)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="identities",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "identities",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="identity",
            unique_together={("provider", "identifier")},
        ),
    ]
