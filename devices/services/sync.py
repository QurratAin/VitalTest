import time
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from ..models import (
    BloodAnalyzer, SyncLog, DataSource,
    TestRun, TestMetric
)
import random

class SyncService:
    """Service for handling device synchronization."""
    
    @staticmethod
    def sync_source(source_id):
        """
        Synchronize all devices from a specific data source.
        
        Args:
            source_id (int): The ID of the data source to sync
            
        Returns:
            SyncLog: The record of the sync operation
        """
        try:
            source = DataSource.objects.get(id=source_id)
            
            # Check if source is active
            if not source.is_active:
                error_msg = f"Data source {source.name} is not active"
                SyncLog.objects.create(
                    source=source,
                    status='failed',
                    error_message=error_msg
                )
                raise ValueError(error_msg)
            
            # Check if source is already syncing
            if SyncLog.objects.filter(
                source=source,
                status='in_progress',
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            ).exists():
                error_msg = f"Source {source.name} is already being synced"
                SyncLog.objects.create(
                    source=source,
                    status='failed',
                    error_message=error_msg
                )
                raise Exception(error_msg)
            
            start_time = timezone.now()
            records_processed = 0
            
            try:
                # Get all devices for this source
                devices = BloodAnalyzer.objects.filter(data_source=source)
                
                for device in devices:
                    # Simulate fetching new test runs from source
                    # In a real implementation, this would connect to the source's database
                    # and fetch actual new/updated records
                    
                    # For factory sources, simulate more frequent test runs
                    if source.source_type == 'factory':
                        num_runs = random.randint(1, 3)  # 1-3 new runs
                        run_prefix = 'F'  # Factory prefix
                    # For cloud sources, simulate fewer but more detailed runs
                    elif source.source_type == 'cloud':
                        num_runs = random.randint(0, 1)  # 0-1 new runs
                        run_prefix = 'C'  # Cloud prefix
                    # For legacy sources, simulate occasional runs
                    else:
                        num_runs = random.randint(0, 1)  # 0-1 new runs
                        run_prefix = 'L'  # Legacy prefix
                    
                    new_runs = [
                        {
                            'run_id': f'TR-{run_prefix}-{timezone.now().strftime("%Y%m%d")}-{i:03d}',
                            'run_type': random.choice(['qc', 'production', 'maintenance']),  # Using string values
                            'is_abnormal': random.random() < 0.1,  # 10% chance of abnormal
                            'is_factory_data': (source.source_type == 'factory'),  # Using string value
                            'executed_by': device.assigned_technician,
                            'notes': f'Test run {i} for {device.device_id}'
                        }
                        for i in range(1, num_runs + 1)
                    ]
                    
                    with transaction.atomic():
                        for run_data in new_runs:
                            # Create test run
                            test_run = TestRun.objects.create(
                                run_id=run_data['run_id'],
                                device=device,
                                run_type=run_data['run_type'],
                                is_abnormal=run_data['is_abnormal'],
                                is_factory_data=run_data['is_factory_data'],
                                data_source=source,
                                executed_by=run_data['executed_by'],
                                notes=run_data['notes']
                            )
                            
                            # Create metrics for the test run
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
                                
                                # For abnormal runs, generate values outside normal range
                                if run_data['is_abnormal']:
                                    if random.random() < 0.5:  # 50% chance of high value
                                        value = expected_max * random.uniform(1.1, 1.5)
                                    else:  # 50% chance of low value
                                        value = expected_min * random.uniform(0.5, 0.9)
                                else:
                                    value = random.uniform(expected_min * 0.9, expected_max * 1.1)
                                
                                TestMetric.objects.create(
                                    test_run=test_run,
                                    metric_type=metric_type,
                                    value=value,
                                    expected_min=expected_min,
                                    expected_max=expected_max
                                )
                            
                            records_processed += 1
                
                # Create sync log record
                sync_log = SyncLog.objects.create(
                    source=source,
                    status='success',
                    records_processed=records_processed
                )
                
                # Update data source last sync time
                source.last_sync = timezone.now()
                source.save()
                
                return sync_log
                
            except Exception as e:
                # Create sync log record for failure
                sync_log = SyncLog.objects.create(
                    source=source,
                    status='failed',
                    error_message=str(e)
                )
                raise
                
        except DataSource.DoesNotExist:
            raise Exception(f"Data source with ID {source_id} not found")
    
    @staticmethod
    def get_sync_status(source_id):
        """
        Get the current sync status of a data source.
        
        Args:
            source_id (int): The ID of the data source
            
        Returns:
            dict: The sync status information
        """
        try:
            source = DataSource.objects.get(id=source_id)
            
            last_sync = SyncLog.objects.filter(
                source=source
            ).order_by('-timestamp').first()
            
            return {
                'source_id': source_id,
                'source_name': source.name,
                'last_sync_time': last_sync.timestamp if last_sync else None,
                'last_sync_status': last_sync.status if last_sync else None,
                'last_error': last_sync.error_message if last_sync else None,
                'is_syncing': SyncLog.objects.filter(
                    source=source,
                    status='in_progress',
                    timestamp__gte=timezone.now() - timedelta(minutes=5)
                ).exists()
            }
        except DataSource.DoesNotExist:
            raise Exception(f"Data source with ID {source_id} not found")
    
    @staticmethod
    def get_sync_history(source_id, limit=10):
        """
        Get the sync history for a data source.
        
        Args:
            source_id (int): The ID of the data source
            limit (int): Maximum number of history records to return
            
        Returns:
            QuerySet: The sync history records
        """
        try:
            source = DataSource.objects.get(id=source_id)
            
            return SyncLog.objects.filter(
                source=source
            ).order_by('-timestamp')[:limit]
        except DataSource.DoesNotExist:
            raise Exception(f"Data source with ID {source_id} not found") 