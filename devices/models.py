from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

class BloodAnalyzer(models.Model):
    class DeviceType(models.TextChoices):
        CORE = 'core', 'VitalOne Core Analyzer'
        MOBILE = 'mobile', 'VitalOne Mobile Unit'
        PROTOTYPE = 'prototype', 'Prototype Device'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CALIBRATION_NEEDED = 'calibration', 'Needs Calibration'
        MAINTENANCE = 'maintenance', 'In Maintenance'
        DECOMMISSIONED = 'decommissioned', 'Decommissioned'

    device_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique device serial number (e.g., VA-205-0001)"
    )
    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.CORE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    last_calibration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last calibration timestamp"
    )
    next_calibration_due = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Automatically set to last_calibration + 30 days"
    )
    location = models.CharField(
        max_length=100,
        help_text="Factory floor/lab location (e.g., 'Factory QA Line 2')"
    )
    manufacturing_date = models.DateField()
    assigned_technician = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_devices',
        help_text="Technician responsible for this device"
    )

    class Meta:
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['status']),
            models.Index(fields=['device_type']),
        ]
        verbose_name = "Blood Analyzer Device"
        verbose_name_plural = "Blood Analyzers"
    
    def __str__(self):
        return f"{self.device_id} ({self.get_device_type_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-set next calibration due date
        if self.last_calibration and not self.next_calibration_due:
            self.next_calibration_due = self.last_calibration + timedelta(days=30)
        super().save(*args, **kwargs)

class TestRun(models.Model):
    class RunType(models.TextChoices):
        QC = 'qc', 'Quality Control Test'
        PRODUCTION = 'production', 'Production Run'
        MAINTENANCE = 'maintenance', 'Maintenance Test'
    
    run_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Batch ID (e.g., TR-20240520-001)"
    )
    device = models.ForeignKey(
        BloodAnalyzer,
        on_delete=models.PROTECT,
        related_name='test_runs'
    )
    run_type = models.CharField(
        max_length=20,
        choices=RunType.choices,
        default=RunType.PRODUCTION
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the test batch was executed"
    )
    is_abnormal = models.BooleanField(
        default=False,
        help_text="Auto-set if any metric fails QC"
    )
    is_factory_data = models.BooleanField(
        default=False,
        help_text="True if data originated from factory machines"
    )
    data_source = models.ForeignKey(
        'DataSource',
        on_delete=models.PROTECT,
        related_name='test_runs'
    )
    executed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='executed_runs',
        help_text="User who performed this test"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional technician comments"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['is_abnormal']),
            models.Index(fields=['run_type']),
        ]
        verbose_name = "Test Run"
        verbose_name_plural = "Test Runs"
    
    def __str__(self):
        return f"{self.run_id} ({self.device.device_id})"

class TestMetric(models.Model):
    class MetricType(models.TextChoices):
        HEMOGLOBIN = 'hgb', 'Hemoglobin (g/dL)'
        WBC = 'wbc', 'White Blood Cells (10³/μL)'
        PLATELETS = 'plt', 'Platelets (10³/μL)'
        GLUCOSE = 'glc', 'Glucose (mg/dL)'
    
    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    metric_type = models.CharField(
        max_length=20,
        choices=MetricType.choices
    )
    value = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Actual measured value"
    )
    expected_min = models.FloatField(
        help_text="Minimum acceptable value for QC"
    )
    expected_max = models.FloatField(
        help_text="Maximum acceptable value for QC"
    )
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(expected_max__gt=models.F('expected_min')),
                name='valid_metric_range'
            ),
            models.UniqueConstraint(
                fields=['test_run', 'metric_type'],
                name='unique_metric_per_run'
            )
        ]
        verbose_name = "Test Metric"
        verbose_name_plural = "Test Metrics"
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value} ({self.test_run.run_id})"
    
    def save(self, *args, **kwargs):
        """Auto-flag abnormal runs when metrics are out of range"""
        if self.value < self.expected_min or self.value > self.expected_max:
            self.test_run.is_abnormal = True
            self.test_run.save()
        super().save(*args, **kwargs)

class DataSource(models.Model):
    class SourceType(models.TextChoices):
        FACTORY = 'factory', 'Factory Database'
        CLOUD = 'cloud', 'Cloud Central'
        LEGACY = 'legacy', 'Legacy System'
    
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Human-readable name (e.g., 'Factory Floor DB')"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices
    )
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful sync timestamp"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable this data source"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['source_type']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"
    
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

class SyncLog(models.Model):
    class SyncStatus(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        PARTIAL = 'partial', 'Partial'
    
    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='sync_logs'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the sync was attempted"
    )
    status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        help_text="Result of the sync operation"
    )
    records_processed = models.IntegerField(
        default=0,
        help_text="Number of records processed in this sync"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details if sync failed"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['source', 'timestamp']),
            models.Index(fields=['status']),
        ]
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"
    
    def __str__(self):
        return f"{self.source.name} sync at {self.timestamp} ({self.get_status_display()})"
