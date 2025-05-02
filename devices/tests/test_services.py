from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from ..models import (
    BloodAnalyzer, DataSource, SyncLog,
    TestRun, TestMetric
)
from ..services.sync import SyncService
from datetime import timedelta

class SyncServiceTests(TestCase):
    def setUp(self):
        # Create a test technician
        self.technician = User.objects.create(
            username='test_tech',
            email='tech@example.com',
            first_name='Test',
            last_name='Technician'
        )
        
        # Create data sources
        self.factory_source = DataSource.objects.create(
            name='Test Factory',
            source_type=DataSource.SourceType.FACTORY,
            is_active=True
        )
        
        self.cloud_source = DataSource.objects.create(
            name='Test Cloud',
            source_type=DataSource.SourceType.CLOUD,
            is_active=True
        )
        
        # Create blood analyzers
        self.factory_device = BloodAnalyzer.objects.create(
            device_id='VA-205-0001',
            device_type='hematology',
            status='active',
            location='Factory Lab',
            manufacturing_date=timezone.now().date(),
            last_calibration=timezone.now(),
            assigned_technician=self.technician,
            data_source=self.factory_source
        )
        
        self.cloud_device = BloodAnalyzer.objects.create(
            device_id='VA-205-0002',
            device_type='chemistry',
            status='active',
            location='Cloud Lab',
            manufacturing_date=timezone.now().date(),
            last_calibration=timezone.now(),
            assigned_technician=self.technician,
            data_source=self.cloud_source
        )

    def test_sync_source_success(self):
        """Test successful sync of a data source"""
        # Perform sync
        sync_log = SyncService.sync_source(self.factory_source.id)
        
        # Verify sync log
        self.assertEqual(sync_log.source, self.factory_source)
        self.assertEqual(sync_log.status, 'success')
        self.assertGreater(sync_log.records_processed, 0)
        self.assertEqual(sync_log.error_message, '')
        
        # Verify test runs were created
        test_runs = TestRun.objects.filter(data_source=self.factory_source)
        self.assertGreater(test_runs.count(), 0)
        
        # Verify metrics were created
        for test_run in test_runs:
            metrics = TestMetric.objects.filter(test_run=test_run)
            self.assertEqual(metrics.count(), 4)  # 4 metric types per run

    def test_sync_source_failure(self):
        """Test sync failure handling"""
        # Deactivate the source to force a failure
        self.factory_source.is_active = False
        self.factory_source.save()
        
        # Attempt sync
        with self.assertRaises(ValueError):
            SyncService.sync_source(self.factory_source.id)
        
        # Verify failure was logged
        sync_log = SyncLog.objects.filter(
            source=self.factory_source,
            status='failed'
        ).first()
        self.assertIsNotNone(sync_log)
        self.assertIsNotNone(sync_log.error_message)

    def test_get_sync_status(self):
        """Test getting sync status"""
        # Create a sync log
        SyncLog.objects.create(
            source=self.factory_source,
            status='success',
            records_processed=10
        )
        
        # Get status
        status = SyncService.get_sync_status(self.factory_source.id)
        
        # Verify status
        self.assertEqual(status['source_id'], self.factory_source.id)
        self.assertEqual(status['source_name'], self.factory_source.name)
        self.assertIsNotNone(status['last_sync_time'])
        self.assertEqual(status['last_sync_status'], 'success')
        self.assertFalse(status['is_syncing'])

    def test_get_sync_history(self):
        """Test getting sync history"""
        # Create multiple sync logs
        for i in range(5):
            SyncLog.objects.create(
                source=self.factory_source,
                status='success',
                records_processed=i * 10
            )
        
        # Get history
        history = SyncService.get_sync_history(self.factory_source.id, limit=3)
        
        # Verify history
        self.assertEqual(history.count(), 3)
        self.assertEqual(history[0].records_processed, 40)  # Most recent
        self.assertEqual(history[2].records_processed, 20)  # Oldest in limit

    def test_sync_source_concurrent(self):
        """Test concurrent sync prevention"""
        # Create an in-progress sync
        SyncLog.objects.create(
            source=self.factory_source,
            status='in_progress',
            timestamp=timezone.now()
        )
        
        # Attempt another sync
        with self.assertRaises(Exception) as context:
            SyncService.sync_source(self.factory_source.id)
        
        self.assertIn('already being synced', str(context.exception))

    def test_sync_source_different_types(self):
        """Test syncing different source types"""
        # Sync factory source
        factory_sync = SyncService.sync_source(self.factory_source.id)
        factory_runs = TestRun.objects.filter(data_source=self.factory_source)
        
        # Sync cloud source
        cloud_sync = SyncService.sync_source(self.cloud_source.id)
        cloud_runs = TestRun.objects.filter(data_source=self.cloud_source)
        
        # Debug logging
        print(f"Factory source type: {self.factory_source.source_type}")
        print(f"Cloud source type: {self.cloud_source.source_type}")
        print(f"Factory runs count: {factory_runs.count()}")
        print(f"Cloud runs count: {cloud_runs.count()}")
        
        # Verify different behavior for different source types
        self.assertGreater(factory_runs.count(), cloud_runs.count())
        
        # Verify metrics for both
        for test_run in factory_runs:
            metrics = TestMetric.objects.filter(test_run=test_run)
            self.assertEqual(metrics.count(), 4)
        
        for test_run in cloud_runs:
            metrics = TestMetric.objects.filter(test_run=test_run)
            self.assertEqual(metrics.count(), 4)
