from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone
from datetime import datetime, timedelta
import random
import logging
import time
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates test data for factory databases every 3 minutes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=180,
            help='Interval in seconds between data generation (default: 180)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.SUCCESS('Starting test data generation...'))

        # Initialize data source in all databases
        try:
            self.data_source_ids = {}
            for db_name in ['default', 'factory_a', 'factory_c']:
                db_path = settings.DATABASES[db_name]['NAME']
                
                # Ensure the database directory exists
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                
                # Connect directly to SQLite to create the table if needed
                with connections[db_name].cursor() as cursor:
                    # Check if devices_datasource table exists
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='devices_datasource'
                    """)
                    table_exists = cursor.fetchone() is not None

                    if not table_exists:
                        # Create the devices_datasource table
                        cursor.execute("""
                            CREATE TABLE devices_datasource (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name varchar(50) NOT NULL,
                                source_type varchar(20) NOT NULL,
                                last_sync datetime NULL,
                                is_active bool NOT NULL
                            )
                        """)
                        self.stdout.write(self.style.SUCCESS(f'Created devices_datasource table in {db_name}'))

                    # Try to get an existing data source
                    cursor.execute("SELECT id FROM devices_datasource LIMIT 1")
                    result = cursor.fetchone()
                    if result:
                        self.data_source_ids[db_name] = result[0]
                    else:
                        # If no data source exists, create one
                        now = timezone.now()
                        # Use the exact database name as the data source name
                        cursor.execute("""
                            INSERT INTO devices_datasource (name, source_type, is_active, last_sync)
                            VALUES (%s, %s, %s, %s)
                        """, [db_name, 'factory', True, now.isoformat()])
                        
                        cursor.execute("SELECT last_insert_rowid()")
                        self.data_source_ids[db_name] = cursor.fetchone()[0]
                        self.stdout.write(self.style.SUCCESS(f'Created default data source in {db_name}'))

        except Exception as e:
            logger.error(f"Error initializing data sources: {str(e)}")
            raise

        while True:
            try:
                # Get analyzers from both factory databases
                factory_a_analyzers = self.get_factory_analyzers('factory_a')
                factory_c_analyzers = self.get_factory_analyzers('factory_c')
                
                # Generate test runs and metrics for each analyzer
                for analyzer in factory_a_analyzers:
                    self.generate_test_run(analyzer, 'factory_a')
                    
                for analyzer in factory_c_analyzers:
                    self.generate_test_run(analyzer, 'factory_c')
                    
                self.stdout.write(self.style.SUCCESS('Successfully generated test data in factory databases'))
                
                # Sleep for the specified interval
                time.sleep(interval)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error generating test data: {str(e)}'))
                logger.error(f'Error generating test data: {str(e)}', exc_info=True)
                time.sleep(60)  # Sleep for 1 minute on error

    def get_factory_analyzers(self, factory_db):
        """Get all analyzers from the specified factory database"""
        with connections[factory_db].cursor() as cursor:
            cursor.execute("SELECT id, device_id FROM devices_bloodanalyzer")
            return [{'id': row[0], 'device_id': row[1]} for row in cursor.fetchall()]

    def generate_test_run(self, analyzer, factory_db):
        """Generate a test run and metrics for an analyzer"""
        try:
            # Create test run
            with connections[factory_db].cursor() as cursor:
                # Generate a unique run_id using timestamp, microseconds, and a random suffix
                now = timezone.now()
                random_suffix = ''.join(random.choices('0123456789ABCDEF', k=4))
                test_run_id = f"{now.strftime('%Y%m%d%H%M%S')}_{now.microsecond:06d}_{random_suffix}_{analyzer['device_id']}"
                
                # Get the first user ID for executed_by_id
                cursor.execute("SELECT id FROM auth_user LIMIT 1")
                user_id = cursor.fetchone()[0]
                
                # Get the first data source ID
                cursor.execute("SELECT id FROM devices_datasource LIMIT 1")
                data_source_id = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO devices_testrun (
                        run_id, device_id, executed_by_id, timestamp, run_type,
                        is_abnormal, is_factory_data, notes, data_source_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    test_run_id,
                    analyzer['id'],
                    user_id,
                    now.isoformat(),
                    'production',
                    False,
                    True,
                    f"Test run for analyzer {analyzer['device_id']}",
                    data_source_id
                ])
                
                # Get the ID of the inserted test run
                cursor.execute("SELECT id FROM devices_testrun WHERE run_id = %s", [test_run_id])
                test_run_db_id = cursor.fetchone()[0]
                
                # Generate test metrics
                self.generate_test_metrics(cursor, test_run_db_id)
                
        except Exception as e:
            logger.error(f"Error generating test run for analyzer {analyzer['device_id']}: {str(e)}")
            raise

    def generate_test_metrics(self, cursor, test_run_id):
        """Generate test metrics for a test run"""
        metrics = [
            ('wbc', 4.0, 11.0),    # White Blood Cells
            ('rbc', 4.0, 6.0),     # Red Blood Cells
            ('hgb', 12.0, 18.0),   # Hemoglobin
            ('hct', 36.0, 54.0),   # Hematocrit
            ('plt', 150.0, 450.0)  # Platelets
        ]
        
        for name, min_val, max_val in metrics:
            value = random.uniform(min_val, max_val)
            cursor.execute("""
                INSERT INTO devices_testmetric (
                    test_run_id, metric_type, value, expected_min, expected_max
                ) VALUES (%s, %s, %s, %s, %s)
            """, [
                test_run_id,
                name,
                value,
                min_val,
                max_val
            ]) 