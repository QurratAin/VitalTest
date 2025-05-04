from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0002_alter_bloodanalyzer_options_and_more'),
    ]

    operations = [
        # This migration will create the tables in all databases
        # because allow_migrate returns True for factory_models
        migrations.AlterModelOptions(
            name='bloodanalyzer',
            options={'verbose_name': 'Blood Analyzer', 'verbose_name_plural': 'Blood Analyzers'},
        ),
        migrations.AlterModelOptions(
            name='testrun',
            options={'verbose_name': 'Test Run', 'verbose_name_plural': 'Test Runs'},
        ),
        migrations.AlterModelOptions(
            name='testmetric',
            options={'verbose_name': 'Test Metric', 'verbose_name_plural': 'Test Metrics'},
        ),
    ] 