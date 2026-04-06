# Generated manually for soft delete + required created_by

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_created_by_for_orphans(apps, schema_editor):
    FinancialRecord = apps.get_model("records", "FinancialRecord")
    User = apps.get_model("accounts", "User")
    qs = FinancialRecord.objects.filter(created_by__isnull=True)
    if qs.exists():
        user = User.objects.order_by("date_joined").first()
        if user:
            qs.update(created_by_id=user.pk)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0002_alter_financialrecord_category_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialrecord",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.RunPython(assign_created_by_for_orphans, noop_reverse),
        migrations.AlterField(
            model_name="financialrecord",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="financial_records",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="financialrecord",
            index=models.Index(fields=["created_by", "is_deleted"], name="financial_r_created_7a8b9c_idx"),
        ),
    ]
