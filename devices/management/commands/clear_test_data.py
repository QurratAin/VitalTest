from django.core.management.base import BaseCommand
from devices.models import BloodAnalyzer, DataSource, SyncLog, TestRun, TestMetric
from django.db.utils import OperationalError
from django.db import connection, connections
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clears all test data from all databases'

    def handle(self, *args, **options):
        self.stdout.write('Clearing test data from all databases...')

        # List of all databases to clear
        databases = ['default', 'factory_a', 'factory_c']

        for db in databases:
            self.stdout.write(f'\nClearing {db} database...')

            try:
                # Delete in correct order (respecting foreign key constraints)
                # 1. TestMetrics (depends on TestRun)
                metrics_count = TestMetric.objects.using(db).count()
                TestMetric.objects.using(db).all().delete()
                self.stdout.write(f'Deleted {metrics_count} test metrics from {db}')
            except OperationalError as e:
                if 'no such table' in str(e):
                    self.stdout.write(f'No test metrics table in {db} database')
                else:
                    raise

            try:
                # 2. TestRuns (depends on BloodAnalyzer)
                if db in ['factory_a', 'factory_c']:
                    # For factory databases, use raw SQL to avoid ORM issues
                    with connections[db].cursor() as cursor:
                        try:
                            # Count test runs
                            cursor.execute("SELECT COUNT(*) FROM devices_testrun")
                            runs_count = cursor.fetchone()[0]
                            
                            # Try to clear data_source references if column exists
                            try:
                                cursor.execute("SELECT data_source_id FROM devices_testrun LIMIT 1")
                                # Delete all test runs
                                cursor.execute("DELETE FROM devices_testrun")
                                self.stdout.write(f'Deleted test runs from {db} database')
                            except Exception as e:
                                if 'no such column' in str(e):
                                    self.stdout.write(f'No data_source column in test runs table in {db} database - skipping data_source cleanup')
                                else:
                                    raise
                            
                            # Delete all test runs
                            cursor.execute("DELETE FROM devices_testrun")
                            self.stdout.write(f'Deleted {runs_count} test runs from {db}')
                        except Exception as e:
                            if 'no such table' in str(e):
                                self.stdout.write(f'No test runs table in {db} database')
                            else:
                                raise
                else:
                    # For default database, use ORM
                    runs_count = TestRun.objects.using(db).count()
                    TestRun.objects.using(db).all().delete()
                    self.stdout.write(f'Deleted {runs_count} test runs from {db}')
            except OperationalError as e:
                if 'no such table' in str(e):
                    self.stdout.write(f'No test runs table in {db} database')
                else:
                    raise

            try:
                # 3. BloodAnalyzers
                if db in ['factory_a', 'factory_c']:
                    # For factory databases, use raw SQL to avoid ORM issues
                    with connections[db].cursor() as cursor:
                        try:
                            # Count devices
                            cursor.execute("SELECT COUNT(*) FROM devices_bloodanalyzer")
                            devices_count = cursor.fetchone()[0]
                            
                            # Try to clear data_source references if column exists
                            try:
                                cursor.execute("SELECT data_source_id FROM devices_bloodanalyzer LIMIT 1")
                                # Delete all devices
                                cursor.execute("DELETE FROM devices_bloodanalyzer")
                                self.stdout.write(f'Deleted blood analyzers from {db} database')
                            except Exception as e:
                                if 'no such column' in str(e):
                                    self.stdout.write(f'No data_source column in blood analyzers table in {db} database - skipping data_source cleanup')
                                else:
                                    raise
                            
                            # Delete all devices
                            cursor.execute("DELETE FROM devices_bloodanalyzer")
                            self.stdout.write(f'Deleted {devices_count} devices from {db}')
                        except Exception as e:
                            if 'no such table' in str(e):
                                self.stdout.write(f'No blood analyzers table in {db} database')
                            else:
                                raise
                else:
                    # For default database, use ORM
                    devices_count = BloodAnalyzer.objects.using(db).count()
                    BloodAnalyzer.objects.using(db).all().delete()
                    self.stdout.write(f'Deleted {devices_count} devices from {db}')
            except OperationalError as e:
                if 'no such table' in str(e):
                    self.stdout.write(f'No blood analyzers table in {db} database')
                else:
                    raise

            # 4. SyncLogs and DataSources (only in default database)
            if db == 'default':
                try:
                    # Delete SyncLogs first (depends on DataSource)
                    sync_logs_count = SyncLog.objects.using(db).count()
                    SyncLog.objects.using(db).all().delete()
                    self.stdout.write(f'Deleted {sync_logs_count} sync logs from {db}')
                except OperationalError as e:
                    if 'no such table' in str(e):
                        self.stdout.write(f'No sync logs table in {db} database')
                    else:
                        raise

                try:
                    # Delete DataSources last (no dependencies)
                    sources_count = DataSource.objects.using(db).filter(source_type='factory').count()
                    DataSource.objects.using(db).filter(source_type='factory').delete()
                    self.stdout.write(f'Deleted {sources_count} factory data sources from {db}')
                except OperationalError as e:
                    if 'no such table' in str(e):
                        self.stdout.write(f'No data sources table in {db} database')
                    else:
                        raise

        self.stdout.write(self.style.SUCCESS('Successfully cleared test data from all databases'))

    def clear_factory_data(self, factory_db):
        """Clear test data from the specified factory database"""
        with connections[factory_db].cursor() as cursor:
            # Delete test metrics first (due to foreign key constraints)
            cursor.execute("DELETE FROM devices_testmetric")
            
            # Delete test runs
            cursor.execute("DELETE FROM devices_testrun")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('devices_testmetric', 'devices_testrun')") 