from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0005_alter_testrun_options'),
    ]

    operations = [
        # No operations needed - this migration is just to ensure proper separation
        # of factory models from system models in the migration history
    ] 