import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OTPRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("otp_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.IntegerField(default=0)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("identity", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="otp_requests",
                    to="identity.identity",
                )),
            ],
            options={
                "db_table": "otp_requests",
                "ordering": ["-created_at"],
            },
        ),
    ]
