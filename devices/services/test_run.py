from devices.models import TestRun, TestMetric, BloodAnalyzer
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User

class TestRunService:
    """Service for handling test run operations."""
    
    @staticmethod
    def sync_analyzer_runs(analyzer: BloodAnalyzer, runs=None):
        """
        Sync test runs for a specific analyzer.
        Returns a tuple of (new_runs_count, new_metrics_count)
        """
        # Map source name to database name
        db_name = analyzer.data_source.name.lower().replace(' ', '_')
        print(f"Syncing runs from {db_name} to default database")
        
        if runs is None:
            runs = TestRun.objects.using(db_name).filter(device=analyzer)
        
        new_runs_count = 0
        new_metrics_count = 0
        
        for run in runs:
            try:
                print(f"Processing run {run.run_id} from {db_name}")
                
                # First, ensure the analyzer exists in the default database
                try:
                    default_analyzer = BloodAnalyzer.objects.using('default').get(device_id=analyzer.device_id)
                except BloodAnalyzer.DoesNotExist:
                    print(f"Creating analyzer {analyzer.device_id} in default database")
                    # Copy analyzer data to default database
                    analyzer_data = {
                        'device_id': analyzer.device_id,
                        'device_type': analyzer.device_type,
                        'status': analyzer.status,
                        'location': analyzer.location,
                        'manufacturing_date': analyzer.manufacturing_date,
                        'last_calibration': analyzer.last_calibration,
                        'next_calibration_due': analyzer.next_calibration_due,
                        'assigned_technician': analyzer.assigned_technician,
                        'data_source': analyzer.data_source
                    }
                    default_analyzer = BloodAnalyzer.objects.using('default').create(**analyzer_data)
                
                # Handle executed_by user before starting transaction
                default_executed_by = None
                if run.executed_by_id:  # Check if there's a user assigned
                    try:
                        # Get the user from the source database
                        source_user = User.objects.using(db_name).get(id=run.executed_by_id)
                        
                        # Try to get the user from default database
                        try:
                            default_executed_by = User.objects.using('default').get(username=source_user.username)
                        except User.DoesNotExist:
                            print(f"Creating user {source_user.username} in default database")
                            # Create the user in default database
                            user_data = {
                                'username': source_user.username,
                                'email': source_user.email,
                                'first_name': source_user.first_name,
                                'last_name': source_user.last_name,
                                'is_staff': source_user.is_staff,
                                'is_active': source_user.is_active
                            }
                            default_executed_by = User.objects.using('default').create(**user_data)
                    except User.DoesNotExist:
                        print(f"Warning: User with ID {run.executed_by_id} not found in {db_name}")
                
                # Check if run already exists in default database
                try:
                    existing_run = TestRun.objects.using('default').get(run_id=run.run_id)
                    print(f"Run {run.run_id} already exists in default database, checking metrics")
                    synced_run = existing_run
                except TestRun.DoesNotExist:
                    # Get all fields from the source run
                    run_data = {
                        'run_id': run.run_id,
                        'run_type': run.run_type,
                        'timestamp': run.timestamp,
                        'is_abnormal': run.is_abnormal,
                        'is_factory_data': True,
                        'notes': run.notes,
                        'data_source': analyzer.data_source,
                        'device': default_analyzer,  # Use the analyzer from default database
                        'executed_by': default_executed_by  # Use the user from default database
                    }
                    
                    # Create the run in the default database
                    with transaction.atomic(using='default'):
                        print(f"Creating new run {run.run_id} in default database")
                        synced_run = TestRun.objects.using('default').create(**run_data)
                        new_runs_count += 1
                
                # Now sync the metrics for this run
                try:
                    metrics = TestMetric.objects.using(db_name).filter(test_run=run)
                    print(f"Found {metrics.count()} metrics for run {run.run_id}")
                    
                    for metric in metrics:
                        try:
                            # Check if metric exists using exact match
                            existing_metric = TestMetric.objects.using('default').get(
                                test_run=synced_run,
                                metric_type=metric.metric_type
                            )
                            print(f"Metric {metric.metric_type} for run {run.run_id} already exists in default database, skipping")
                            continue
                        except TestMetric.DoesNotExist:
                            try:
                                # Create new metric
                                TestMetric.objects.using('default').create(
                                    test_run=synced_run,
                                    metric_type=metric.metric_type,
                                    value=metric.value,
                                    expected_min=metric.expected_min,
                                    expected_max=metric.expected_max
                                )
                                new_metrics_count += 1
                                print(f"Created new metric {metric.metric_type} for run {run.run_id}")
                            except Exception as e:
                                print(f"Error creating metric {metric.metric_type} for run {run.run_id}: {str(e)}")
                                raise  # Re-raise to trigger transaction rollback
                except Exception as e:
                    print(f"Error syncing metrics for run {run.run_id}: {str(e)}")
                    raise  # Re-raise to trigger transaction rollback
                    
            except Exception as e:
                print(f"Error syncing run {run.run_id}: {str(e)}")
                continue
        
        print(f"Sync completed. New runs: {new_runs_count}, New metrics: {new_metrics_count}")
        return new_runs_count, new_metrics_count 