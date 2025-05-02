from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from ..models import (
    BloodAnalyzer, DataSource, SyncLog,
    TestRun, TestMetric
)
from datetime import timedelta

class ModelTests(TestCase):
    def setUp(self):
        # Create a test technician
        self.technician = User.objects.create(
            username='test_tech',
            email='tech@example.com',
            first_name='Test',
            last_name='Technician'
        )
        
        # Create a data source
        self.data_source = DataSource.objects.create(
            name='Test Factory',
            source_type='factory',
            is_active=True
        )
        
        # Create a blood analyzer
        self.device = BloodAnalyzer.objects.create(
            device_id='VA-205-0001',
            device_type=BloodAnalyzer.DeviceType.PRODUCTION,
            status='active',
            location='Test Lab',
            manufacturing_date=timezone.now().date(),
            last_calibration=timezone.now(),
            assigned_technician=self.technician,
            data_source=self.data_source
        )

    def test_blood_analyzer_creation(self):
        """Test BloodAnalyzer model creation and validation"""
        # Test device creation
        self.assertEqual(self.device.device_id, 'VA-205-0001')
        self.assertEqual(self.device.device_type, BloodAnalyzer.DeviceType.PRODUCTION)
        self.assertEqual(self.device.status, 'active')
        self.assertEqual(self.device.location, 'Test Lab')
        self.assertEqual(self.device.assigned_technician, self.technician)
        self.assertEqual(self.device.data_source, self.data_source)
        
        # Test device status choices
        self.assertIn(self.device.status, [choice[0] for choice in BloodAnalyzer.Status.choices])
        
        # Test device type choices
        self.assertIn(self.device.device_type, [choice[0] for choice in BloodAnalyzer.DeviceType.choices])

    def test_data_source_creation(self):
        """Test DataSource model creation and validation"""
        # Test source creation
        self.assertEqual(self.data_source.name, 'Test Factory')
        self.assertEqual(self.data_source.source_type, 'factory')
        self.assertTrue(self.data_source.is_active)
        
        # Test source type choices
        self.assertIn(self.data_source.source_type, [choice[0] for choice in DataSource.SourceType.choices])
        
        # Test source string representation
        self.assertEqual(str(self.data_source), 'Test Factory (Factory Database)')

    def test_sync_log_creation(self):
        """Test SyncLog model creation and validation"""
        # Create a sync log
        sync_log = SyncLog.objects.create(
            source=self.data_source,
            status='success',
            records_processed=10
        )
        
        # Test sync log creation
        self.assertEqual(sync_log.source, self.data_source)
        self.assertEqual(sync_log.status, 'success')
        self.assertEqual(sync_log.records_processed, 10)
        self.assertEqual(sync_log.error_message, '')
        
        # Test sync status choices
        self.assertIn(sync_log.status, [choice[0] for choice in SyncLog.SyncStatus.choices])
        
        # Test sync log string representation
        expected_str = f"Test Factory sync at {sync_log.timestamp} (Success)"
        self.assertEqual(str(sync_log), expected_str)

    def test_test_run_creation(self):
        """Test TestRun model creation and validation"""
        # Create a test run
        test_run = TestRun.objects.create(
            run_id='TR-20240315-001',
            device=self.device,
            run_type='routine',
            is_abnormal=False,
            is_factory_data=True,
            data_source=self.data_source,
            executed_by=self.technician,
            notes='Test run'
        )
        
        # Test test run creation
        self.assertEqual(test_run.run_id, 'TR-20240315-001')
        self.assertEqual(test_run.device, self.device)
        self.assertEqual(test_run.run_type, 'routine')
        self.assertFalse(test_run.is_abnormal)
        self.assertTrue(test_run.is_factory_data)
        self.assertEqual(test_run.data_source, self.data_source)
        self.assertEqual(test_run.executed_by, self.technician)
        self.assertEqual(test_run.notes, 'Test run')

    def test_test_metric_creation(self):
        """Test TestMetric model creation and validation"""
        # Create a test run first
        test_run = TestRun.objects.create(
            run_id='TR-20240315-001',
            device=self.device,
            run_type='routine',
            is_abnormal=False,
            is_factory_data=True,
            data_source=self.data_source,
            executed_by=self.technician
        )
        
        # Create a test metric
        test_metric = TestMetric.objects.create(
            test_run=test_run,
            metric_type='hgb',
            value=15.0,
            expected_min=12.0,
            expected_max=18.0
        )
        
        # Test test metric creation
        self.assertEqual(test_metric.test_run, test_run)
        self.assertEqual(test_metric.metric_type, 'hgb')
        self.assertEqual(test_metric.value, 15.0)
        self.assertEqual(test_metric.expected_min, 12.0)
        self.assertEqual(test_metric.expected_max, 18.0)
        
        # Test metric type choices
        self.assertIn(test_metric.metric_type, [choice[0] for choice in TestMetric.MetricType.choices])
