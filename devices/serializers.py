from rest_framework import serializers
from .models import (
    BloodAnalyzer, DataSource, SyncLog,
    TestRun, TestMetric
)

class DataSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for DataSource model.

    Fields:
    - id: Unique identifier
    - name: Display name of the data source
    - source_type: Type of source (factory/cloud/legacy)
    - last_sync: Timestamp of last successful sync
    - is_active: Whether the source is currently active
    """
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'source_type', 'last_sync', 'is_active']
        read_only_fields = ['last_sync']

class SyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for SyncLog model.

    Fields:
    - id: Unique identifier
    - source: Associated data source
    - timestamp: When the sync operation occurred
    - status: Sync status (success/failed/in_progress)
    - records_processed: Number of records processed
    - error_message: Details of any errors that occurred
    """
    source = DataSourceSerializer(read_only=True)
    
    class Meta:
        model = SyncLog
        fields = ['id', 'source', 'timestamp', 'status', 'records_processed', 'error_message']
        read_only_fields = ['timestamp', 'status', 'records_processed', 'error_message']

class BloodAnalyzerSerializer(serializers.ModelSerializer):
    """
    Serializer for BloodAnalyzer model.

    Fields:
    - device_id: Unique identifier for the device (e.g., VA-205-0001)
    - device_type: Type of device (production/prototype/research)
    - status: Current status of the device (active/inactive/maintenance)
    - location: Physical location of the device
    - manufacturing_date: Date when the device was manufactured
    - last_calibration: Last calibration date and time
    - next_calibration_due: Next scheduled calibration date
    - assigned_technician: User responsible for the device
    - data_source: Source system where the device is registered
    """
    class Meta:
        model = BloodAnalyzer
        fields = [
            'device_id', 'device_type', 'status', 'location',
            'manufacturing_date', 'last_calibration', 'next_calibration_due',
            'assigned_technician', 'data_source'
        ]
        read_only_fields = ['next_calibration_due']

class SyncRequestSerializer(serializers.Serializer):
    """
    Serializer for sync request data.

    Fields:
    - device_id: ID of the device to sync
    - force: Whether to force a sync even if one is in progress
    """
    device_id = serializers.CharField()
    force = serializers.BooleanField(default=False)

class SyncStatusSerializer(serializers.Serializer):
    """
    Serializer for sync status information.

    Fields:
    - source_id: ID of the data source
    - source_name: Name of the data source
    - last_sync_time: Timestamp of last successful sync
    - last_sync_status: Status of last sync operation
    - is_syncing: Whether a sync is currently in progress
    """
    source_id = serializers.IntegerField()
    source_name = serializers.CharField()
    last_sync_time = serializers.DateTimeField(required=False)
    last_sync_status = serializers.CharField()
    is_syncing = serializers.BooleanField()

class TestMetricSerializer(serializers.ModelSerializer):
    """
    Serializer for TestMetric model.

    Fields:
    - id: Unique identifier
    - test_run: Associated test run
    - metric_type: Type of metric (hgb/wbc/plt/glc)
    - value: Measured value
    - expected_min: Minimum expected value
    - expected_max: Maximum expected value
    - is_out_of_range: Whether the value is outside expected range (computed)
    """
    is_out_of_range = serializers.SerializerMethodField()

    class Meta:
        model = TestMetric
        fields = [
            'id', 'test_run', 'metric_type', 'value',
            'expected_min', 'expected_max', 'is_out_of_range'
        ]
        read_only_fields = ['is_out_of_range']

    def get_is_out_of_range(self, obj):
        return obj.value < obj.expected_min or obj.value > obj.expected_max

class TestRunSerializer(serializers.ModelSerializer):
    """
    Serializer for TestRun model.

    Fields:
    - id: Unique identifier
    - run_id: Unique run identifier (e.g., TR-20240520-001)
    - device: Associated blood analyzer
    - run_type: Type of run (qc/production/maintenance)
    - timestamp: When the test run was executed
    - is_abnormal: Whether any metrics were out of range
    - is_factory_data: Whether data originated from factory
    - data_source: Source of the test data
    - executed_by: User who performed the test
    - notes: Optional technician comments
    - metrics: Associated test metrics
    """
    device = BloodAnalyzerSerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    executed_by = serializers.StringRelatedField()
    metrics = TestMetricSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestRun
        fields = [
            'id', 'run_id', 'device', 'run_type', 'timestamp',
            'is_abnormal', 'is_factory_data', 'data_source',
            'executed_by', 'notes', 'metrics'
        ]
        read_only_fields = ['timestamp', 'is_abnormal'] 