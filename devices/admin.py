from django.contrib import admin
from django.utils.html import format_html
from .models import BloodAnalyzer, TestRun, TestMetric, DataSource, SyncLog

@admin.register(BloodAnalyzer)
class BloodAnalyzerAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'device_type', 'status', 'location', 'assigned_technician', 'last_calibration', 'next_calibration_due')
    list_filter = ('device_type', 'status', 'location')
    search_fields = ('device_id', 'location')
    list_editable = ('status', 'location')
    readonly_fields = ('next_calibration_due',)
    date_hierarchy = 'manufacturing_date'
    ordering = ('-last_calibration',)
    
    fieldsets = (
        ('Device Information', {
            'fields': ('device_id', 'device_type', 'status', 'location', 'manufacturing_date')
        }),
        ('Calibration', {
            'fields': ('last_calibration', 'next_calibration_due')
        }),
        ('Assignment', {
            'fields': ('assigned_technician',)
        }),
    )

@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ('run_id', 'device', 'run_type', 'timestamp', 'is_abnormal', 'is_factory_data', 'executed_by')
    list_filter = ('run_type', 'is_abnormal', 'is_factory_data', 'data_source', 'timestamp')
    search_fields = ('run_id', 'device__device_id', 'notes')
    readonly_fields = ('timestamp', 'is_abnormal')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Run Information', {
            'fields': ('run_id', 'device', 'run_type', 'timestamp')
        }),
        ('Data Source', {
            'fields': ('data_source', 'is_factory_data')
        }),
        ('Results', {
            'fields': ('is_abnormal', 'notes')
        }),
        ('Execution', {
            'fields': ('executed_by',)
        }),
    )

@admin.register(TestMetric)
class TestMetricAdmin(admin.ModelAdmin):
    list_display = ('test_run', 'metric_type', 'value', 'expected_min', 'expected_max', 'is_out_of_range')
    list_filter = ('metric_type', 'test_run__run_type')
    search_fields = ('test_run__run_id',)
    readonly_fields = ('is_out_of_range',)
    
    def is_out_of_range(self, obj):
        if obj.value < obj.expected_min or obj.value > obj.expected_max:
            return format_html('<span style="color: red;">Out of Range</span>')
        return format_html('<span style="color: green;">In Range</span>')
    is_out_of_range.short_description = 'Range Status'
    
    fieldsets = (
        ('Test Information', {
            'fields': ('test_run', 'metric_type')
        }),
        ('Values', {
            'fields': ('value', 'expected_min', 'expected_max', 'is_out_of_range')
        }),
    )

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'last_sync', 'is_active', 'sync_status')
    list_filter = ('source_type', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('last_sync',)
    
    def sync_status(self, obj):
        if not obj.last_sync:
            return format_html('<span style="color: orange;">Never Synced</span>')
        return format_html('<span style="color: green;">Last Sync: {}</span>', obj.last_sync)
    sync_status.short_description = 'Sync Status'

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('source', 'timestamp', 'status', 'records_processed', 'error_status')
    list_filter = ('status', 'source', 'timestamp')
    search_fields = ('source__name', 'error_message')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    def error_status(self, obj):
        if obj.status == 'failed':
            return format_html('<span style="color: red;">Failed</span>')
        elif obj.status == 'partial':
            return format_html('<span style="color: orange;">Partial</span>')
        return format_html('<span style="color: green;">Success</span>')
    error_status.short_description = 'Error Status'
    
    fieldsets = (
        ('Sync Information', {
            'fields': ('source', 'timestamp', 'status')
        }),
        ('Results', {
            'fields': ('records_processed', 'error_message')
        }),
    )
