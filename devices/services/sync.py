import time
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from ..models import (
    BloodAnalyzer, SyncLog, DataSource,
    TestRun, TestMetric
)
import random
from devices.services.analyzer import AnalyzerService
from devices.services.test_run import TestRunService
from devices.services.test_metric import TestMetricService
from devices.services.sync_log import SyncLogService
from celery import shared_task

class SyncService:
    """Service for handling device synchronization."""
    
    @staticmethod
    def sync_source(source_name: str):
        """
        Sync data from a source database to the default database.
        """
        try:
            # Map source name to database name
            db_name = source_name.lower().replace(' ', '_')
            print(f"Starting sync from {db_name} to default database")
            
            # Get the source object for this sync
            try:
                source = DataSource.objects.using('default').get(name=source_name)
            except DataSource.DoesNotExist:
                print(f"Creating {source_name} data source in default database")
                source = DataSource.objects.using('default').create(
                    name=source_name,
                    source_type='factory',
                    is_active=True
                )
            
            # Create sync log
            sync_log = SyncLog.objects.using('default').create(
                source=source,
                status='in_progress',
                records_processed=0
            )
            
            records_processed = 0
            
            try:
                # Get all analyzers from the source database
                analyzers = BloodAnalyzer.objects.using(db_name).all()
                print(f"Found {analyzers.count()} analyzers in {db_name}")
                
                # Sync each analyzer
                for analyzer in analyzers:
                    try:
                        # Check if analyzer exists in default database
                        try:
                            default_analyzer = BloodAnalyzer.objects.using('default').get(device_id=analyzer.device_id)
                            print(f"Analyzer {analyzer.device_id} already exists in default database, updating...")
                            
                            # Update existing analyzer
                            for field in ['device_type', 'status', 'location', 'manufacturing_date', 
                                        'last_calibration', 'next_calibration_due']:
                                setattr(default_analyzer, field, getattr(analyzer, field))
                            
                            # Handle assigned_technician
                            if analyzer.assigned_technician_id:
                                try:
                                    # Get the technician from source database
                                    source_technician = User.objects.using(db_name).get(id=analyzer.assigned_technician_id)
                                    
                                    # Try to get the technician from default database
                                    try:
                                        default_technician = User.objects.using('default').get(username=source_technician.username)
                                    except User.DoesNotExist:
                                        print(f"Creating technician {source_technician.username} in default database")
                                        # Create the technician in default database
                                        default_technician = User.objects.using('default').create(
                                            username=source_technician.username,
                                            email=source_technician.email,
                                            first_name=source_technician.first_name,
                                            last_name=source_technician.last_name,
                                            is_staff=source_technician.is_staff,
                                            is_active=source_technician.is_active
                                        )
                                    
                                    default_analyzer.assigned_technician = default_technician
                                except User.DoesNotExist:
                                    print(f"Warning: Technician with ID {analyzer.assigned_technician_id} not found in {db_name}")
                                    default_analyzer.assigned_technician = None
                            
                            # Set data source to source (not default)
                            default_analyzer.data_source = source
                            
                            default_analyzer.save(using='default')
                            
                        except BloodAnalyzer.DoesNotExist:
                            print(f"Creating analyzer {analyzer.device_id} in default database")
                            
                            # Handle assigned_technician
                            default_technician = None
                            if analyzer.assigned_technician_id:
                                try:
                                    # Get the technician from source database
                                    source_technician = User.objects.using(db_name).get(id=analyzer.assigned_technician_id)
                                    
                                    # Try to get the technician from default database
                                    try:
                                        default_technician = User.objects.using('default').get(username=source_technician.username)
                                    except User.DoesNotExist:
                                        print(f"Creating technician {source_technician.username} in default database")
                                        # Create the technician in default database
                                        default_technician = User.objects.using('default').create(
                                            username=source_technician.username,
                                            email=source_technician.email,
                                            first_name=source_technician.first_name,
                                            last_name=source_technician.last_name,
                                            is_staff=source_technician.is_staff,
                                            is_active=source_technician.is_active
                                        )
                                except User.DoesNotExist:
                                    print(f"Warning: Technician with ID {analyzer.assigned_technician_id} not found in {db_name}")
                            
                            # Create analyzer in default database
                            analyzer_data = {
                                'device_id': analyzer.device_id,
                                'device_type': analyzer.device_type,
                                'status': analyzer.status,
                                'location': analyzer.location,
                                'manufacturing_date': analyzer.manufacturing_date,
                                'last_calibration': analyzer.last_calibration,
                                'next_calibration_due': analyzer.next_calibration_due,
                                'assigned_technician': default_technician,
                                'data_source': source  # Use the source, not default
                            }
                            default_analyzer = BloodAnalyzer.objects.using('default').create(**analyzer_data)
                        
                        # Sync runs for this analyzer
                        runs = TestRun.objects.using(db_name).filter(device=analyzer)
                        print(f"Found {runs.count()} runs for analyzer {analyzer.device_id}")
                        
                        # Sync runs and get count of new metrics
                        new_runs_count, new_metrics_count = TestRunService.sync_analyzer_runs(analyzer, runs)
                        records_processed += new_metrics_count  # Only count new metrics
                        
                    except Exception as e:
                        print(f"Error syncing analyzer {analyzer.device_id}: {str(e)}")
                        continue
                
                # Update sync log with success
                sync_log.status = 'success'
                sync_log.records_processed = records_processed
                sync_log.save(using='default')
                
                # Update last_sync in DataSource
                source.last_sync = timezone.now()
                source.save(using='default')
                
                print(f"Sync completed successfully. Processed {records_processed} records.")
                return True
                
            except Exception as e:
                print(f"Error during sync: {str(e)}")
                # Update sync log with error
                sync_log.status = 'failed'
                sync_log.records_processed = records_processed
                sync_log.error_message = str(e)
                sync_log.save(using='default')
                return False
                
        except Exception as e:
            print(f"Error creating sync log: {str(e)}")
            return False

    @staticmethod
    def sync_all_sources() -> list[SyncLog]:
        """
        Sync data from all sources.
        """
        sources = DataSource.objects.filter(is_active=True)
        logs = []
        
        for source in sources:
            try:
                log = SyncService.sync_source(source.name)
                logs.append(log)
            except Exception as e:
                print(f"Error syncing source {source.name}: {str(e)}")
                continue
            
        return logs

@shared_task
def periodic_sync():
    """
    Celery task to periodically sync all sources.
    """
    while True:
        try:
            # Get all active data sources
            active_sources = DataSource.objects.filter(is_active=True)
            
            for source in active_sources:
                try:
                    # Check if source needs syncing
                    last_sync = SyncLog.objects.filter(
                        source=source,
                        status='completed'
                    ).order_by('-timestamp').first()
                    
                    # If never synced or last sync was more than 2 minutes ago
                    if not last_sync or (timezone.now() - last_sync.timestamp).total_seconds() > 120:
                        SyncService.sync_source(source.name)
                except Exception as e:
                    print(f"Error syncing source {source.name}: {str(e)}")
                    continue
                    
            time.sleep(60)  # Sleep for 1 minute
        except Exception as e:
            print(f"Error in periodic sync: {str(e)}")
            time.sleep(30)  # Sleep for 30 seconds on error
    
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