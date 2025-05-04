from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0006_separate_factory_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bloodanalyzer',
            name='data_source',
            field=models.ForeignKey(
                'DataSource',
                on_delete=models.PROTECT,
                related_name='devices',
                help_text="Source system where this device is registered",
                null=True,
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='testrun',
            name='data_source',
            field=models.ForeignKey(
                'DataSource',
                on_delete=models.PROTECT,
                related_name='test_runs',
                null=True,
                blank=True
            ),
        ),
    ] 