from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth.models import User
from devices.models import (
    BloodAnalyzer, DataSource, SyncLog,
    TestRun, TestMetric
)

class Command(BaseCommand):
    help = 'Populates the database with test data for devices and sync logs'

    def handle(self, *args, **options):
        self.stdout.write('Clearing existing test data...')
        
        # Delete all existing data in reverse order of dependencies
        TestMetric.objects.all().delete()
        TestRun.objects.all().delete()
        SyncLog.objects.all().delete()
        BloodAnalyzer.objects.all().delete()
        DataSource.objects.filter(source_type__in=['factory', 'research']).delete()
        User.objects.filter(username__in=['test_tech1', 'test_tech2', 'test_tech3']).delete()
        
        self.stdout.write('Creating new test data...')

        # Create test technicians
        technicians = []
        for i in range(1, 4):
            technician = User.objects.create(
                username=f'test_tech{i}',
                email=f'tech{i}@example.com',
                first_name=f'Test',
                last_name=f'Technician {i}',
                is_staff=True
            )
            technician.set_password('testpass123')
            technician.save()
            technicians.append(technician)
            self.stdout.write(f'Created technician: {technician.username}')

        # Create data sources
        data_sources = []
        sources = [
            ('Factory A Database', 'factory', 'Factory A'),
            ('Factory B Database', 'factory', 'Factory B'),
            ('Research Lab Database', 'research', 'Research Lab')
        ]
        
        for name, source_type, location in sources:
            source = DataSource.objects.create(
                name=name,
                source_type=source_type,
                last_sync=timezone.now() - timedelta(hours=1),
                is_active=True
            )
            data_sources.append(source)
            self.stdout.write(f'Created data source: {source.name}')

        # Create test devices (10 devices total)
        device_types = [t[0] for t in BloodAnalyzer.DeviceType.choices]
        device_statuses = [s[0] for s in BloodAnalyzer.Status.choices]
        
        devices = []
        run_counter = 1
        for i in range(1, 11):  # Create 10 devices
            # Distribute devices across data sources
            data_source = data_sources[i % len(data_sources)]
            technician = technicians[i % len(technicians)]
            
            device = BloodAnalyzer.objects.create(
                device_id=f'VA-205-{i:04d}',
                device_type=random.choice(device_types),
                status=random.choice(device_statuses),
                location=f'{data_source.name} Line {random.randint(1, 3)}',
                manufacturing_date=timezone.now().date() - timedelta(days=random.randint(0, 365)),
                last_calibration=timezone.now() - timedelta(days=random.randint(0, 30)),
                assigned_technician=technician,
                data_source=data_source
            )
            devices.append(device)
            self.stdout.write(f'Created device: {device.device_id} in {data_source.name}')

            # Create test runs for each device (6 runs per device)
            for j in range(6):
                run_type = random.choice([t[0] for t in TestRun.RunType.choices])
                test_run = TestRun.objects.create(
                    run_id=f'TR-{timezone.now().strftime("%Y%m%d")}-{run_counter:03d}',
                    device=device,
                    run_type=run_type,
                    is_factory_data=(data_source.source_type == 'factory'),
                    data_source=data_source,
                    executed_by=technician,
                    notes=f'Test run {j+1} for {device.device_id}'
                )
                run_counter += 1

                # Create metrics for each test run
                metric_types = [t[0] for t in TestMetric.MetricType.choices]
                for metric_type in metric_types:
                    # Define expected ranges for each metric type
                    ranges = {
                        'hgb': (12.0, 18.0),  # Hemoglobin
                        'wbc': (4.0, 11.0),   # White Blood Cells
                        'plt': (150.0, 450.0), # Platelets
                        'glc': (70.0, 140.0)  # Glucose
                    }
                    expected_min, expected_max = ranges[metric_type]
                    value = random.uniform(expected_min * 0.9, expected_max * 1.1)
                    
                    TestMetric.objects.create(
                        test_run=test_run,
                        metric_type=metric_type,
                        value=value,
                        expected_min=expected_min,
                        expected_max=expected_max
                    )

        # Create sync logs for each device (20 logs per device)
        for device in devices:
            for i in range(20):
                sync_time = timezone.now() - timedelta(hours=i*2)
                status = random.choice([s[0] for s in SyncLog.SyncStatus.choices])
                
                # Set error message based on status
                if status == 'failed':
                    error_message = random.choice([
                        'Connection timeout',
                        'Database error',
                        'Network error',
                        'Invalid data format'
                    ])
                else:
                    error_message = ''  # Empty string for successful or partial syncs
                
                SyncLog.objects.create(
                    source=device.data_source,
                    timestamp=sync_time,
                    status=status,
                    records_processed=random.randint(1, 100) if status == 'success' else 0,
                    error_message=error_message
                )
            self.stdout.write(f'Created sync logs for device: {device.device_id}')

        self.stdout.write(self.style.SUCCESS('Successfully populated test data')) 