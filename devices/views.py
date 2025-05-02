from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import BloodAnalyzer, SyncLog, DataSource, TestRun, TestMetric
from .serializers import (
    BloodAnalyzerSerializer,
    SyncLogSerializer,
    SyncStatusSerializer,
    SyncRequestSerializer,
    TestRunSerializer,
    TestMetricSerializer
)
from .services.sync import SyncService
from .tasks import sync_device_task

# Create your views here.

class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Vital Tools - Device Performance & Sync System'
        return context

class BloodAnalyzerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing blood analyzer devices.

    list:
    Return a list of all blood analyzers.

    retrieve:
    Return a specific blood analyzer by device_id.

    create:
    Create a new blood analyzer.

    update:
    Update an existing blood analyzer.

    partial_update:
    Partially update an existing blood analyzer.

    destroy:
    Delete a blood analyzer.

    sync:
    Trigger a sync operation for a specific device.

    sync_status:
    Get the current sync status for a device.

    sync_history:
    Get the sync history for a device.
    """
    queryset = BloodAnalyzer.objects.all()
    serializer_class = BloodAnalyzerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'device_id'

    @action(detail=True, methods=['post'])
    def sync(self, request, device_id=None):
        """
        Trigger a sync operation for a specific device.

        This endpoint starts a background task to synchronize data for the specified device.
        Returns a task ID that can be used to track the sync progress.
        """
        serializer = SyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = sync_device_task.delay(device_id)
            return Response({
                'message': 'Sync started',
                'task_id': task.id
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def sync_status(self, request, device_id=None):
        """
        Get the current sync status for a device.

        Returns the latest sync status including:
        - Last sync time
        - Sync status (success/failed/in_progress)
        - Number of records processed
        - Any error messages
        """
        try:
            status = SyncService.get_sync_status(device_id)
            serializer = SyncStatusSerializer(status)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def sync_history(self, request, device_id=None):
        """
        Get the sync history for a device.

        Returns a list of all sync operations performed for the device,
        including timestamps, status, and number of records processed.
        """
        try:
            history = SyncService.get_sync_history(device_id)
            serializer = SyncLogSerializer(history, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing sync logs.

    list:
    Return a list of all sync logs, with optional filtering by:
    - device_id: Filter logs for a specific device
    - status: Filter by sync status (success/failed/in_progress)
    - timestamp: Sort by timestamp (use ordering=-timestamp for descending)

    retrieve:
    Return a specific sync log by ID.
    """
    queryset = SyncLog.objects.all()
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['source', 'status', 'timestamp']
    ordering_fields = ['timestamp', 'records_processed']
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device_id', None)
        if device_id:
            try:
                device = BloodAnalyzer.objects.get(device_id=device_id)
                factory_source = DataSource.objects.get(source_type='factory')
                queryset = queryset.filter(source=factory_source)
            except (BloodAnalyzer.DoesNotExist, DataSource.DoesNotExist):
                return SyncLog.objects.none()
        return queryset

class TestRunViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing test runs.

    list:
    Return a list of all test runs, with optional filtering by:
    - device_id: Filter runs for a specific device
    - run_type: Filter by run type (qc/production/maintenance)
    - is_abnormal: Filter by abnormal status
    - timestamp: Sort by timestamp

    retrieve:
    Return a specific test run by ID.

    create:
    Create a new test run.

    update:
    Update an existing test run.

    partial_update:
    Partially update an existing test run.

    destroy:
    Delete a test run.

    metrics:
    Get all metrics for a specific test run.
    """
    queryset = TestRun.objects.all()
    serializer_class = TestRunSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['device', 'run_type', 'is_abnormal', 'is_factory_data', 'timestamp']
    ordering_fields = ['timestamp', 'run_id']
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device_id', None)
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """
        Get all metrics for a specific test run.

        Returns a list of all metrics associated with the test run,
        including values, expected ranges, and out-of-range status.
        """
        test_run = self.get_object()
        metrics = test_run.metrics.all()
        serializer = TestMetricSerializer(metrics, many=True)
        return Response(serializer.data)
