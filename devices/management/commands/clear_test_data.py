from django.core.management.base import BaseCommand
from devices.models import BloodAnalyzer, DataSource, SyncLog, TestRun, TestMetric

class Command(BaseCommand):
    help = 'Clears all test data from the database'

    def handle(self, *args, **options):
        self.stdout.write('Clearing test data...')

        # Delete in correct order (respecting foreign key constraints)
        # 1. TestMetrics (depends on TestRun)
        metrics_count = TestMetric.objects.count()
        TestMetric.objects.all().delete()
        self.stdout.write(f'Deleted {metrics_count} test metrics')

        # 2. TestRuns (depends on BloodAnalyzer and DataSource)
        runs_count = TestRun.objects.count()
        TestRun.objects.all().delete()
        self.stdout.write(f'Deleted {runs_count} test runs')

        # 3. SyncLogs (depends on DataSource)
        sync_logs_count = SyncLog.objects.count()
        SyncLog.objects.all().delete()
        self.stdout.write(f'Deleted {sync_logs_count} sync logs')

        # 4. BloodAnalyzers (depends on DataSource)
        devices_count = BloodAnalyzer.objects.count()
        BloodAnalyzer.objects.all().delete()
        self.stdout.write(f'Deleted {devices_count} devices')

        # 5. DataSources (no dependencies)
        sources_count = DataSource.objects.filter(source_type='factory').count()
        DataSource.objects.filter(source_type='factory').delete()
        self.stdout.write(f'Deleted {sources_count} factory data sources')

        self.stdout.write(self.style.SUCCESS('Successfully cleared test data')) 