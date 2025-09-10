from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    UnifiedLoginView, RegisterView,
    HiringManagerViewSet, VideoCampaignViewSet,
    InterviewSessionViewSet, EvaluationViewSet,
    CampaignShareViewSet, CampaignAnalyticsView,
    CandidateSessionAccessView, StartInterviewView,
    VideoSettingsViewSet, DashboardMetricsViewSet, 
    AIAnalysisViewSet, QuestionViewSet, 
    CandidateViewSet, VideoResponseViewSet, 
    SessionLogViewSet, PresignUploadView,
    SubmitInterviewResponsesView
)

router = DefaultRouter()
router.register(r'hiring-managers', HiringManagerViewSet, basename='hiring-manager')
router.register(r'campaigns', VideoCampaignViewSet, basename='campaign')
router.register(r'sessions', InterviewSessionViewSet, basename='session')
router.register(r'evaluations', EvaluationViewSet, basename='evaluation')
router.register(r'campaign-shares', CampaignShareViewSet, basename='campaign-share')
router.register(r'video-settings', VideoSettingsViewSet, basename='video-settings')
router.register(r'dashboard-metrics', DashboardMetricsViewSet, basename='dashboard-metrics')
router.register(r'ai-analysis', AIAnalysisViewSet, basename='ai-analysis')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'responses', VideoResponseViewSet, basename='response')
router.register(r'logs', SessionLogViewSet, basename='log')

urlpatterns = [
    # Public candidate access (avoid conflict with router 'sessions')
    path('session-access/<uuid:access_token>/', CandidateSessionAccessView.as_view(), name='candidate-session-access'),
    path('session-access/<uuid:access_token>/start/', StartInterviewView.as_view(), name='start-interview'),
    path('sessions/<uuid:session_id>/submit/', SubmitInterviewResponsesView.as_view(), name='submit-interview-responses'),

    # Routered API (this file is expected to be included under /api/ by backend/urls.py)
    path('', include(router.urls)),

    # Auth (relative paths; backend mounts this file under /api/)
    path('auth/login/', UnifiedLoginView.as_view(), name='unified-login'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Campaign analytics endpoint
    path('campaigns/<uuid:campaign_id>/analytics/', CampaignAnalyticsView.as_view(), name='campaign-analytics'),

    # Presigned URL for uploads
    path('uploads/presign/', PresignUploadView.as_view(), name='presign-upload'),
]
