from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BloodAnalyzerViewSet, SyncLogViewSet, TestRunViewSet

# Create the router
router = DefaultRouter()
router.register(r'devices', BloodAnalyzerViewSet, basename='device')
router.register(r'sync-logs', SyncLogViewSet, basename='sync-log')
router.register(r'test-runs', TestRunViewSet, basename='test-run')

# Define URL patterns for the devices app
urlpatterns = [
    # Add any non-API URLs here if needed
]

# Export the router for use in the main URL configuration
__all__ = ['router', 'urlpatterns'] 