from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_aifilejob_docs_creation_in_progress"),
    ]

    operations = [
        migrations.AddField(
            model_name="aifilejob",
            name="source_ai_job",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="derived_ai_jobs",
                to="core.aifilejob",
            ),
        ),
    ]
