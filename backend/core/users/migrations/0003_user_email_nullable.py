from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_managers_alter_user_groups_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
    ]
