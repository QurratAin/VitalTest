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
    API endpoint for managing blood analyzers.
    """
    queryset = BloodAnalyzer.objects.all()
    serializer_class = BloodAnalyzerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'device_id'

    @action(detail=True, methods=['post'])
    def sync(self, request, device_id=None):
        """
        Trigger a sync operation for a specific device.
        """
        serializer = SyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Start sync in background
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
        Get all metrics for a test run.
        """
        test_run = self.get_object()
        metrics = test_run.metrics.all()
        serializer = TestMetricSerializer(metrics, many=True)
        return Response(serializer.data)
