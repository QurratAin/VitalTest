from celery import shared_task
from django.utils import timezone
from .services.sync import SyncService
from .models import BloodAnalyzer, DataSource
import time

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

@shared_task
def periodic_sync_task():
    """
    Celery task to perform periodic sync of all active devices.
    This task runs every 30 minutes and syncs devices that haven't synced in the last 30 minutes.
    """
    factory_source = DataSource.objects.get(source_type='factory')
    active_devices = BloodAnalyzer.objects.filter(status='active')
    
    for device in active_devices:
        try:
            status = SyncService.get_sync_status(device.device_id)
            
            # If device hasn't synced in the last 30 minutes, trigger a sync
            if status['last_sync_time'] is None or \
               (timezone.now() - status['last_sync_time']).total_seconds() > 1800:
                sync_device_task.delay(device.device_id)
                
        except Exception as e:
            print(f"Error in periodic sync for device {device.device_id}: {str(e)}")
            continue

@shared_task
def sync_all_sources():
    """
    Single task that checks all active data sources for new data.
    If no new data is found, sleeps for 10 minutes before checking again.
    """
    print("Starting sync_all_sources task...")
    active_sources = DataSource.objects.filter(is_active=True)
    print(f"Found {active_sources.count()} active sources")
    new_data_found = False
    
    for source in active_sources:
        try:
            print(f"Processing source: {source.name}")
            # Check if source needs syncing
            status = SyncService.get_sync_status(source.id)
            print(f"Source {source.name} status: {status}")
            
            # If source hasn't synced in the last hour or never synced
            if status['last_sync_time'] is None or \
               (timezone.now() - status['last_sync_time']).total_seconds() > 3600:
                
                print(f"Source {source.name} needs syncing")
                # Try to sync the source
                try:
                    sync_result = SyncService.sync_source(source)
                    if sync_result.records_processed > 0:
                        new_data_found = True
                        print(f"Synced {sync_result.records_processed} records from {source.name}")
                    else:
                        print(f"No records processed for {source.name}")
                except Exception as e:
                    print(f"Error syncing source {source.name}: {str(e)}")
                    continue
            else:
                print(f"Source {source.name} doesn't need syncing yet")
                    
        except Exception as e:
            print(f"Error checking sync status for source {source.name}: {str(e)}")
            continue
    
    # If no new data was found, sleep for 10 minutes
    if not new_data_found:
        print("No new data found. Sleeping for 10 minutes...")
        time.sleep(600)  # Sleep for 10 minutes
    
    # Schedule next check
    print("Scheduling next sync check...")
    sync_all_sources.delay() 