from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UnifiedLoginView, UserProfileView,
    HiringManagerViewSet, VideoCampaignViewSet, QuestionViewSet,
    CandidateViewSet, InterviewSessionViewSet, VideoResponseViewSet,
    SessionLogViewSet, AIAnalysisViewSet, CandidateSessionsView, RegisterView,
    generate_presigned_url, VideoUploadCompleteView, HiringManagerCreateView,
    CampaignAnalyticsView, RecruiterDashboardView, EvaluationViewSet, CampaignShareViewSet
)

router = DefaultRouter()
router.register(r'hiring-managers', HiringManagerViewSet, basename='hiring-manager')
router.register(r'campaigns', VideoCampaignViewSet, basename='campaign')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'sessions', InterviewSessionViewSet, basename='session')
router.register(r'responses', VideoResponseViewSet, basename='response')
router.register(r'logs', SessionLogViewSet, basename='log')
router.register(r'ai-analysis', AIAnalysisViewSet, basename='ai-analysis')

urlpatterns = [
    # Authentification unifiée
    path('auth/login/', UnifiedLoginView.as_view(), name='unified-login'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/candidate/sessions/', CandidateSessionsView.as_view(), name='candidate-sessions'),
    path('upload/init/<uuid:session_id>/', generate_presigned_url, name='upload-init'),
    path('upload/complete/<uuid:session_id>/<uuid:question_id>/', 
         VideoUploadCompleteView.as_view(), name='upload-complete'),
    path('api/hiring-managers/create/', HiringManagerCreateView.as_view(), name='hiringmanager-create'),
    # API REST
    path('api/', include(router.urls)),
    path('api/campaigns/<uuid:campaign_id>/analytics/', CampaignAnalyticsView.as_view(), name='campaign-analytics'),

    path('api/hiring-managers/dashboard/', RecruiterDashboardView.as_view(), name='recruiter-dashboard'),
    path('api/campaigns/<uuid:campaign_id>/analytics/', CampaignAnalyticsView.as_view(), name='campaign-analytics'),

    # Évaluations
    path('api/evaluations/', EvaluationViewSet.as_view({'get': 'list', 'post': 'create'}), name='evaluation-list'),
    path('api/evaluations/pending/', EvaluationViewSet.as_view({'get': 'pending_evaluations'}), name='pending-evaluations'),
    path('api/evaluations/<int:pk>/', EvaluationViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='evaluation-detail'),
    
    # Partage de campagnes
    path('api/campaign-shares/', CampaignShareViewSet.as_view({'get': 'list', 'post': 'create'}), name='campaignshare-list'),
    path('api/campaign-shares/<int:pk>/', CampaignShareViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='campaignshare-detail'),
]
urlpatterns += [
    path('auth/register/', RegisterView.as_view(), name='register'),
    
]
