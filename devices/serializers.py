from rest_framework import serializers
from .models import (
    BloodAnalyzer, DataSource, SyncLog,
    TestRun, TestMetric
)

class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'source_type', 'last_sync', 'is_active']
        read_only_fields = ['last_sync']

class SyncLogSerializer(serializers.ModelSerializer):
    source = DataSourceSerializer(read_only=True)
    
    class Meta:
        model = SyncLog
        fields = ['id', 'source', 'timestamp', 'status', 'records_processed', 'error_message']
        read_only_fields = ['timestamp', 'status', 'records_processed', 'error_message']

class BloodAnalyzerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodAnalyzer
        fields = ['device_id', 'device_type', 'status', 'last_calibration', 'next_calibration_due', 'location', 'manufacturing_date', 'assigned_technician']
        read_only_fields = ['next_calibration_due']

class SyncRequestSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    force = serializers.BooleanField(default=False)

class SyncStatusSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    last_sync = serializers.DateTimeField()
    status = serializers.CharField()
    error_message = serializers.CharField(allow_blank=True)

class TestMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestMetric
        fields = ['id', 'metric_type', 'value', 'expected_min', 'expected_max']
        read_only_fields = ['test_run']

class TestRunSerializer(serializers.ModelSerializer):
    device = BloodAnalyzerSerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    executed_by = serializers.StringRelatedField()
    metrics = TestMetricSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestRun
        fields = ['id', 'run_id', 'device', 'run_type', 'timestamp', 'is_abnormal', 'is_factory_data', 'data_source', 'executed_by', 'notes', 'metrics']
        read_only_fields = ['timestamp', 'is_abnormal'] 