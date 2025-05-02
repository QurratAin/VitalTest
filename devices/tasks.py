from celery import shared_task
from django.utils import timezone
from .services.sync import SyncService
from .models import BloodAnalyzer, DataSource

@shared_task
def sync_device_task(device_id):
    """
    Celery task to sync a device's data in the background.
    
    Args:
        device_id (str): The ID of the device to sync
    """
    try:
        return SyncService.sync_device(device_id)
    except Exception as e:
        # Log the error and re-raise
        print(f"Error syncing device {device_id}: {str(e)}")
        raise

@shared_task
def sync_all_devices_task():
    """
    Celery task to sync all active devices in the background.
    """
    factory_source = DataSource.objects.get(source_type='factory')
    active_devices = BloodAnalyzer.objects.filter(status='active')
    
    for device in active_devices:
        try:
            sync_device_task.delay(device.device_id)
        except Exception as e:
            print(f"Error scheduling sync for device {device.device_id}: {str(e)}")
            continue

@shared_task
def check_sync_status_task():
    """
    Celery task to check sync status of all devices and trigger sync if needed.
    """
    factory_source = DataSource.objects.get(source_type='factory')
    active_devices = BloodAnalyzer.objects.filter(status='active')
    
    for device in active_devices:
        try:
            status = SyncService.get_sync_status(device.device_id)
            
            # If device hasn't synced in the last hour, trigger a sync
            if status['last_sync_time'] is None or \
               (timezone.now() - status['last_sync_time']).total_seconds() > 3600:
                sync_device_task.delay(device.device_id)
                
        except Exception as e:
            print(f"Error checking sync status for device {device.device_id}: {str(e)}")
            continue 