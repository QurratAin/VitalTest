from devices.models import SyncLog, DataSource
from django.utils import timezone

class SyncLogService:
    @staticmethod
    def create_log(source: DataSource) -> SyncLog:
        """
        Create a new sync log entry.
        """
        return SyncLog.objects.create(
            source=source,
            status='in_progress',  # This will be updated to 'success' or 'failed'
            timestamp=timezone.now(),
            error_message=''  # Initialize with empty string
        )

    @staticmethod
    def update_log(log: SyncLog, status: str, records_processed: int = 0, error_message: str = None):
        """
        Update a sync log entry with the final status and results.
        """
        # Map the status to the correct choice
        status_map = {
            'completed': 'success',
            'failed': 'failed',
            'partial': 'partial'
        }
        
        # Update all fields
        log.status = status_map.get(status, status)  # Use mapped status or fallback to original
        log.records_processed = records_processed
        log.error_message = error_message if error_message is not None else ''
        log.timestamp = timezone.now()
        
        # Save the log first
        log.save()
        
        # Then update the data source's last sync time if successful
        if log.status == 'success':  # Use the mapped status here too
            log.source.last_sync = timezone.now()
            log.source.save() 