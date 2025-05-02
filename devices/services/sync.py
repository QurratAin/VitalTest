import time
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from ..models import BloodAnalyzer, SyncLog, DataSource

class SyncService:
    """Service for handling device synchronization."""
    
    @staticmethod
    def sync_device(device_id):
        """
        Synchronize a device's data with the cloud database.
        
        Args:
            device_id (str): The ID of the device to sync
            
        Returns:
            SyncLog: The record of the sync operation
        """
        try:
            device = BloodAnalyzer.objects.get(device_id=device_id)
            factory_source = DataSource.objects.get(source_type='factory')
            
            # Check if device is already syncing
            if SyncLog.objects.filter(
                source=factory_source,
                status='in_progress',
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            ).exists():
                raise Exception("Device is already being synced")
            
            start_time = timezone.now()
            
            try:
                # TODO: Implement actual data sync logic here
                # This is where you would:
                # 1. Connect to the factory database
                # 2. Fetch new/updated records
                # 3. Upload them to the cloud database
                
                # Simulate sync process
                time.sleep(2)  # Simulate network delay
                records_processed = 10  # Simulate syncing 10 records
                
                # Create sync log record
                sync_log = SyncLog.objects.create(
                    source=factory_source,
                    status='success',
                    records_processed=records_processed
                )
                
                # Update data source last sync time
                factory_source.last_sync = timezone.now()
                factory_source.save()
                
                return sync_log
                
            except Exception as e:
                # Create sync log record for failure
                sync_log = SyncLog.objects.create(
                    source=factory_source,
                    status='failed',
                    error_message=str(e)
                )
                raise
                
        except BloodAnalyzer.DoesNotExist:
            raise Exception(f"Device with ID {device_id} not found")
        except DataSource.DoesNotExist:
            raise Exception("Factory data source not configured")
    
    @staticmethod
    def get_sync_status(device_id):
        """
        Get the current sync status of a device.
        
        Args:
            device_id (str): The ID of the device
            
        Returns:
            dict: The sync status information
        """
        try:
            device = BloodAnalyzer.objects.get(device_id=device_id)
            factory_source = DataSource.objects.get(source_type='factory')
            
            last_sync = SyncLog.objects.filter(
                source=factory_source
            ).order_by('-timestamp').first()
            
            return {
                'device_id': device_id,
                'last_sync_time': last_sync.timestamp if last_sync else None,
                'last_sync_status': last_sync.status if last_sync else None,
                'last_error': last_sync.error_message if last_sync else None,
                'is_syncing': SyncLog.objects.filter(
                    source=factory_source,
                    status='in_progress',
                    timestamp__gte=timezone.now() - timedelta(minutes=5)
                ).exists()
            }
        except (BloodAnalyzer.DoesNotExist, DataSource.DoesNotExist):
            raise Exception(f"Device or data source not found")
    
    @staticmethod
    def get_sync_history(device_id, limit=10):
        """
        Get the sync history for a device.
        
        Args:
            device_id (str): The ID of the device
            limit (int): Maximum number of history records to return
            
        Returns:
            QuerySet: The sync history records
        """
        try:
            device = BloodAnalyzer.objects.get(device_id=device_id)
            factory_source = DataSource.objects.get(source_type='factory')
            
            return SyncLog.objects.filter(
                source=factory_source
            ).order_by('-timestamp')[:limit]
        except (BloodAnalyzer.DoesNotExist, DataSource.DoesNotExist):
            raise Exception(f"Device or data source not found") 