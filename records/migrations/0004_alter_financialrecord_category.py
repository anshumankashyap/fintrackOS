# Category validation moved to serializer; DB stores plain string.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0003_financialrecord_is_deleted_and_owner_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialrecord",
            name="category",
            field=models.CharField(db_index=True, max_length=100),
        ),
    ]
