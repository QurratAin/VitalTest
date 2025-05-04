from devices.models import TestMetric, TestRun
from django.db import transaction

class TestMetricService:
    """Service for handling test metric operations."""
    
    @staticmethod
    def sync_run_metrics(run: TestRun, metrics=None):
        """
        Sync test metrics for a specific test run.
        """
        if metrics is None:
            metrics = TestMetric.objects.filter(test_run=run)
        
        for metric in metrics:
            try:
                # Get all fields from the source metric
                metric_data = {
                    'test_run': run,
                    'metric_type': metric.metric_type,
                    'value': metric.value,
                    'expected_min': metric.expected_min,
                    'expected_max': metric.expected_max
                }
                
                # Create or update the metric in the default database
                with transaction.atomic(using='default'):
                    # Try to get existing metric
                    existing_metric = TestMetric.objects.using('default').filter(
                        test_run=run,
                        metric_type=metric.metric_type
                    ).first()
                    
                    if existing_metric:
                        # Update existing metric
                        for field, value in metric_data.items():
                            setattr(existing_metric, field, value)
                        existing_metric.save(using='default')
                    else:
                        # Create new metric
                        TestMetric.objects.using('default').create(**metric_data)
                        
            except Exception as e:
                print(f"Error syncing metric {metric.id}: {str(e)}")
                continue
            
        return metrics 