from devices.models import BloodAnalyzer, TestRun
from django.utils import timezone

class AnalyzerService:
    @staticmethod
    def sync_analyzer_runs(analyzer: BloodAnalyzer) -> list[TestRun]:
        """
        Sync test runs for a specific analyzer.
        Returns a list of newly created or updated test runs.
        """
        # In a real implementation, this would fetch data from the source database
        # For now, we'll just return the latest runs
        return list(TestRun.objects.filter(device=analyzer).order_by('-timestamp')[:10]) 