import uuid
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
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "organizations",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(
                    choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member")],
                    default="member",
                    max_length=50,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="memberships",
                    to="organizations.organization",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="memberships",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "memberships",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="membership",
            unique_together={("user", "organization")},
        ),
    ]
