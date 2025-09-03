from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from datetime import timedelta
import uuid
import traceback
from django.db import IntegrityError, models

from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, action
from rest_framework import generics, viewsets, status, filters
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

# ... le reste de vos imports ...

from .models import (
    HiringManager, VideoCampaign, Question, Candidate,
    InterviewSession, VideoResponse, SessionLog, AIAnalysis, 
    DashboardMetrics, Evaluation, CampaignShare
)
from .serializers import (
    HiringManagerSerializer, VideoCampaignSerializer, QuestionSerializer,
    CandidateSerializer, VideoResponseSerializer, SessionLogSerializer,
    AIAnalysisSerializer, InterviewSessionSerializer, CreateCampaignSerializer,
    InviteCandidateSerializer, StartSessionSerializer, SubmitVideoResponseSerializer,
    UserSerializer, DashboardMetricsSerializer, EvaluationSerializer, CampaignShareSerializer
)
from django.contrib.auth import get_user_model
User = get_user_model()
# Vos classes de vues ici...

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        user = User.objects.create_user(
            username=request.data['username'],
            email=request.data['email'],
            password=request.data['password']
        )
        return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

class UnifiedLoginView(APIView):
    """Vue de connexion unifiée pour tous les types d'utilisateurs"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email et mot de passe requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trouver l'utilisateur par email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'Identifiants invalides'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Authentifier l'utilisateur avec son username
        user = authenticate(username=user.username, password=password)
        
        if not user:
            return Response({
                'error': 'Identifiants invalides'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Vérifier que l'utilisateur est actif
        if not user.is_active:
            return Response({
                'error': 'Compte désactivé'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Récupérer le profil utilisateur
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Profil utilisateur non trouvé'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        # Préparer la réponse selon le type d'utilisateur
        response_data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_type': profile.user_type,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        # Ajouter des informations spécifiques selon le type
        if profile.is_hiring_manager:
            try:
                hiring_manager = profile.hiring_manager
                response_data.update({
                    'company': hiring_manager.company,
                    'department': hiring_manager.department,
                    'phone': hiring_manager.phone,
                })
            except HiringManager.DoesNotExist:
                pass
        elif profile.is_candidate:
            try:
                candidate = Candidate.objects.get(email=user.email)
                response_data.update({
                    'candidate_id': str(candidate.id),
                    'phone': candidate.phone,
                    'linkedin_url': candidate.linkedin_url,
                })
            except Candidate.DoesNotExist:
                pass
        
        return Response(response_data)

class UserProfileView(APIView):
    """Vue pour récupérer le profil de l'utilisateur connecté"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.profile
            response_data = {
                'user_type': profile.user_type,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
            
            if profile.is_hiring_manager:
                try:
                    hiring_manager = profile.hiring_manager
                    response_data.update({
                        'company': hiring_manager.company,
                        'department': hiring_manager.department,
                        'phone': hiring_manager.phone,
                    })
                except HiringManager.DoesNotExist:
                    pass
            elif profile.is_candidate:
                try:
                    candidate = Candidate.objects.get(email=request.user.email)
                    response_data.update({
                        'candidate_id': str(candidate.id),
                        'phone': candidate.phone,
                        'linkedin_url': candidate.linkedin_url,
                    })
                except Candidate.DoesNotExist:
                    pass
            
            return Response(response_data)
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Profil utilisateur non trouvé'
            }, status=status.HTTP_400_BAD_REQUEST)

class HiringManagerViewSet(viewsets.ModelViewSet):
    """Gestion des Hiring Managers"""
    serializer_class = HiringManagerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return HiringManager.objects.filter(user_profile__user=self.request.user)

class VideoCampaignViewSet(viewsets.ModelViewSet):
    """Gestion des campagnes d'entretien vidéo"""
    serializer_class = VideoCampaignSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        # Vérifier le type d'utilisateur
        if hasattr(self.request.user, 'profile') and self.request.user.profile.is_hiring_manager:
            # Recruteur : voir ses propres campagnes
            return VideoCampaign.objects.filter(hiring_manager__user_profile__user=self.request.user)
        else:
            # Candidat : voir les campagnes auxquelles il est invité
            return VideoCampaign.objects.filter(sessions__candidate__email=self.request.user.email).distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateCampaignSerializer
        return VideoCampaignSerializer
    
    @action(detail=True, methods=['post'])
    def invite_candidates(self, request, pk=None):
        """Inviter des candidats à une campagne"""
        campaign = self.get_object()
        serializer = InviteCandidateSerializer(data=request.data, many=True)
        
        if serializer.is_valid():
            invited_candidates = []
            
            for candidate_data in serializer.validated_data:
                # Créer ou récupérer le candidat
                candidate, created = Candidate.objects.get_or_create(
                    email=candidate_data['email'],
                    defaults=candidate_data
                )
                
                # Créer la session d'entretien
                session = InterviewSession.objects.create(
                    campaign=campaign,
                    candidate=candidate,
                    expires_at=campaign.end_date,
                    total_questions=campaign.questions.count()
                )
                
                # Log de l'invitation
                SessionLog.objects.create(
                    session=session,
                    log_type='session_start',
                    message=f'Candidat invité: {candidate.email}'
                )
                
                invited_candidates.append({
                    'candidate': candidate.email,
                    'access_token': session.access_token,
                    'invite_url': f"/interview/{session.access_token}"
                })
            
            return Response({
                'message': f'{len(invited_candidates)} candidats invités',
                'invited_candidates': invited_candidates
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Statistiques de la campagne"""
        campaign = self.get_object()
        
        stats = {
            'total_sessions': campaign.sessions.count(),
            'completed_sessions': campaign.sessions.filter(status='completed').count(),
            'in_progress_sessions': campaign.sessions.filter(status='in_progress').count(),
            'expired_sessions': campaign.sessions.filter(status='expired').count(),
            'total_responses': VideoResponse.objects.filter(session__campaign=campaign).count(),
            'average_duration': campaign.sessions.aggregate(
                avg_duration=models.Avg('total_duration')
            )['avg_duration'] or 0
        }
        
        return Response(stats)

class QuestionViewSet(viewsets.ModelViewSet):
    """Gestion des questions"""
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Question.objects.filter(campaign__hiring_manager__user=self.request.user)

class CandidateViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des candidats (lecture seule)"""
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['email', 'first_name', 'last_name']
    
    def get_queryset(self):
        return Candidate.objects.filter(
            interviews__campaign__hiring_manager__user=self.request.user
        ).distinct()

class InterviewSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des sessions d'entretien"""
    serializer_class = InterviewSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['candidate__email', 'candidate__first_name', 'candidate__last_name']
    ordering_fields = ['invited_at', 'started_at', 'completed_at']
    
    def get_queryset(self):
        return InterviewSession.objects.filter(
            campaign__hiring_manager__user=self.request.user
        )
    
    @action(detail=False, methods=['post'])
    def start_session(self, request):
        """Démarrer une session avec un token d'accès"""
        serializer = StartSessionSerializer(data=request.data)
        
        if serializer.is_valid():
            access_token = serializer.validated_data['access_token']
            
            try:
                session = InterviewSession.objects.get(
                    access_token=access_token,
                    status__in=['invited', 'started'],
                    expires_at__gt=timezone.now()
                )
                
                if session.status == 'invited':
                    session.status = 'started'
                    session.started_at = timezone.now()
                    session.save()
                
                # Log du démarrage
                SessionLog.objects.create(
                    session=session,
                    log_type='session_start',
                    message='Session démarrée par le candidat'
                )
                
                return Response({
                    'session_id': session.id,
                    'campaign': VideoCampaignSerializer(session.campaign).data,
                    'candidate': CandidateSerializer(session.candidate).data,
                    'questions': QuestionSerializer(session.campaign.questions.all(), many=True).data
                })
                
            except InterviewSession.DoesNotExist:
                return Response(
                    {'error': 'Session invalide ou expirée'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@action(detail=True, methods=['post'])
def submit_response(self, request, pk=None):
    """Soumettre une réponse vidéo avec gestion complète des erreurs"""
    session = self.get_object()
    serializer = SubmitVideoResponseSerializer(data=request.data)
    
    # Validation initiale du serializer
    if not serializer.is_valid():
        SessionLog.objects.create(
            session=session,
            log_type='error',
            message="Données de réponse invalides",
            metadata={'errors': serializer.errors}
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Récupération de la question
    try:
        question_id = request.data.get('question_id')
        question = Question.objects.get(id=question_id, campaign=session.campaign)
    except Question.DoesNotExist:
        SessionLog.objects.create(
            session=session,
            log_type='error',
            message=f"Question introuvable: ID {question_id}",
            metadata={'question_id': question_id}
        )
        return Response(
            {'error': 'Question invalide'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        SessionLog.objects.create(
            session=session,
            log_type='error',
            message=f"Erreur de récupération de la question: {str(e)}",
            metadata={'question_id': question_id, 'error': str(e)}
        )
        return Response(
            {'error': 'Erreur technique'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Tentative de création de la réponse vidéo
    try:
        video_response = VideoResponse.objects.create(
            session=session,
            question=question,
            video_file=serializer.validated_data['video_file'],
            duration=serializer.validated_data['duration'],
            preparation_time_used=serializer.validated_data.get('preparation_time_used', 0),
            response_time_used=serializer.validated_data.get('response_time_used', 0)
        )
        
        # Mise à jour atomique des compteurs
        InterviewSession.objects.filter(id=session.id).update(
            answered_questions=models.F('answered_questions') + 1,
            total_duration=models.F('total_duration') + video_response.duration
        )
        
        # Log de succès
        SessionLog.objects.create(
            session=session,
            log_type='video_record',
            message=f'Réponse enregistrée pour Q{question.order}',
            metadata={
                'question_id': question.id,
                'duration': video_response.duration
            }
        )
        
        return Response({
            'message': 'Réponse enregistrée avec succès',
            'response_id': str(video_response.id),
            'remaining_questions': session.total_questions - (session.answered_questions + 1)
        }, status=status.HTTP_201_CREATED)
        
    except IntegrityError as e:
        SessionLog.objects.create(
            session=session,
            log_type='error',
            message="Erreur d'intégrité base de données",
            metadata={'error': str(e), 'question_id': question.id}
        )
        return Response(
            {'error': 'Conflit de données'},
            status=status.HTTP_409_CONFLICT
        )
        
    except IOError as e:
        SessionLog.objects.create(
            session=session,
            log_type='error',
            message="Erreur de stockage du fichier vidéo",
            metadata={'error': str(e)}
        )
        return Response(
            {'error': 'Échec du stockage vidéo'},
            status=status.HTTP_507_INSUFFICIENT_STORAGE
        )
        
    except Exception as e:
        SessionLog.objects.create(
            session=session,
            log_type='critical',
            message=f"Erreur inattendue: {str(e)}",
            metadata={
                'error_type': type(e).__name__,
                'question_id': question.id,
                'stack_trace': traceback.format_exc()
            }
        )
        return Response(
            {'error': 'Échec technique'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @action(detail=True, methods=['post'])
    def complete_session(self, request, pk=None):
        """Marquer la session comme terminée"""
        session = self.get_object()
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()
        
        # Log de la completion
        SessionLog.objects.create(
            session=session,
            log_type='session_complete',
            message='Session terminée par le candidat'
        )
        
        return Response({'message': 'Session terminée'})

class VideoResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des réponses vidéo"""
    serializer_class = VideoResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['recorded_at', 'duration']
    
    def get_queryset(self):
        return VideoResponse.objects.filter(
            session__campaign__hiring_manager__user=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        """Évaluer une réponse vidéo"""
        video_response = self.get_object()
        score = request.data.get('score')
        notes = request.data.get('notes', '')
        
        if score is not None:
            video_response.score = score
            video_response.notes = notes
            video_response.evaluated_by = request.user.hiring_manager
            video_response.evaluated_at = timezone.now()
            video_response.save()
            
            return Response({'message': 'Réponse évaluée'})
        
        return Response(
            {'error': 'Score requis'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

class SessionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des logs de session"""
    serializer_class = SessionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp']
    
    def get_queryset(self):
        return SessionLog.objects.filter(
            session__campaign__hiring_manager__user=self.request.user
        )

class AIAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des analyses IA"""
    serializer_class = AIAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AIAnalysis.objects.filter(
            video_response__session__campaign__hiring_manager__user=self.request.user
        )
    

class CandidateSessionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        candidate = get_object_or_404(Candidate, user=request.user)
        sessions = InterviewSession.objects.filter(candidate=candidate)
        serializer = InterviewSessionSerializer(sessions, many=True)
        return Response(serializer.data)

from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import FileUploadParser
import boto3
from datetime import datetime, timedelta

#upload video initiation
@csrf_exempt
@api_view(['POST'])
def generate_presigned_url(request, session_id):
    """Génère une URL pré-signée pour upload direct vers S3"""
    session = get_object_or_404(InterviewSession, id=session_id)
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    object_key = f"video_responses/{session_id}/{datetime.now().isoformat()}.webm"
    presigned_url = s3.generate_presigned_post(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=object_key,
        ExpiresIn=3600  # 1 heure
    )
    
    return Response({
        'presigned_url': presigned_url,
        'object_key': object_key
    })

#upload video complete
class VideoUploadCompleteView(APIView):
    parser_classes = [FileUploadParser]
    #permission_classes = [IsAuthenticated]

    def post(self, request, session_id, question_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        question = get_object_or_404(Question, id=question_id)
        
        try:
            video_response = VideoResponse.objects.create(
                session=session,
                question=question,
                video_url=request.data.get('file_url'),
                upload_status='completed',
                file_size=request.data.get('file_size'),
                format=request.data.get('format')
            )
            return Response({'status': 'success'}, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        

# interviews/views.py
from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from .models import HiringManager
from .serializers import HiringManagerSerializer

class HiringManagerCreateView(generics.CreateAPIView):
    """
    Vue pour créer un HiringManager
    """
    queryset = HiringManager.objects.all()
    serializer_class = HiringManagerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user_id = self.request.data.get('user_id')
        if not user_id:
            raise serializers.ValidationError({"user_id": "Ce champ est requis"})
        
        user = get_object_or_404(User, id=user_id)
        serializer.save(user=user)


##views pour les evaluations

# Ajoutez ces vues à votre fichier views.py

class EvaluationViewSet(viewsets.ModelViewSet):
    """Gestion des évaluations par les recruteurs"""
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Les recruteurs ne voient que leurs évaluations
        return Evaluation.objects.filter(
            hiring_manager__user_profile__user=self.request.user
        ).select_related(
            'video_response__session__candidate',
            'video_response__question',
            'video_response__session__campaign'
        )
    
    def perform_create(self, serializer):
        # Associe automatiquement le hiring_manager connecté
        hiring_manager = HiringManager.objects.get(
            user_profile__user=self.request.user
        )
        serializer.save(hiring_manager=hiring_manager)
    
    @action(detail=False, methods=['get'])
    def pending_evaluations(self, request):
        """Réponses vidéo non encore évaluées"""
        hiring_manager = HiringManager.objects.get(
            user_profile__user=request.user
        )
        
        unevaluated_responses = VideoResponse.objects.filter(
            session__campaign__hiring_manager=hiring_manager,
            evaluation__isnull=True
        ).select_related('session__candidate', 'question', 'session__campaign')
        
        page = self.paginate_queryset(unevaluated_responses)
        serializer = VideoResponseSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

class RecruiterDashboardView(APIView):
    """Tableau de bord personnalisé pour le recruteur"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            hiring_manager = HiringManager.objects.get(
                user_profile__user=request.user
            )
        except HiringManager.DoesNotExist:
            return Response(
                {"error": "Profil recruteur non trouvé"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Métriques principales
        total_campaigns = VideoCampaign.objects.filter(
            hiring_manager=hiring_manager
        ).count()
        
        active_campaigns = VideoCampaign.objects.filter(
            hiring_manager=hiring_manager,
            is_active=True,
            end_date__gte=timezone.now()
        ).count()
        
        # Statistiques avancées
        campaign_stats = VideoCampaign.objects.filter(
            hiring_manager=hiring_manager
        ).annotate(
            total_candidates=Count('sessions'),
            completed_interviews=Count('sessions', filter=Q(sessions__status='completed')),
            avg_rating=Avg('sessions__responses__evaluation__overall_score')
        ).values('id', 'title', 'total_candidates', 'completed_interviews', 'avg_rating')
        
        # Évaluations récentes
        recent_evaluations = Evaluation.objects.filter(
            hiring_manager=hiring_manager
        ).select_related(
            'video_response__session__candidate',
            'video_response__question'
        ).order_by('-evaluated_at')[:5]
        
        data = {
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'campaign_stats': campaign_stats,
            'recent_evaluations': EvaluationSerializer(recent_evaluations, many=True).data,
            'upcoming_deadlines': self.get_upcoming_deadlines(hiring_manager)
        }
        
        return Response(data)
    
    def get_upcoming_deadlines(self, hiring_manager):
        """Campagnes avec échéance proche (7 jours)"""
        seven_days_later = timezone.now() + timedelta(days=7)
        return VideoCampaign.objects.filter(
            hiring_manager=hiring_manager,
            end_date__lte=seven_days_later,
            end_date__gte=timezone.now(),
            is_active=True
        ).values('id', 'title', 'end_date')

class CampaignAnalyticsView(APIView):
    """Analyses détaillées par campagne"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, campaign_id):
        try:
            campaign = VideoCampaign.objects.get(
                id=campaign_id,
                hiring_manager__user_profile__user=request.user
            )
        except VideoCampaign.DoesNotExist:
            return Response(
                {"error": "Campagne non trouvée ou accès non autorisé"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        analytics = {
            'completion_rate': self.get_completion_rate(campaign),
            'average_duration': self.get_average_duration(campaign),
            'question_analytics': self.get_question_analytics(campaign),
            'candidate_performance': self.get_candidate_performance(campaign)
        }
        
        return Response(analytics)
    
    def get_completion_rate(self, campaign):
        total = campaign.sessions.count()
        completed = campaign.sessions.filter(status='completed').count()
        return (completed / total * 100) if total > 0 else 0
    
    def get_average_duration(self, campaign):
        return campaign.sessions.aggregate(
            avg_duration=Avg('total_duration')
        )['avg_duration'] or 0
    
    def get_question_analytics(self, campaign):
        return Question.objects.filter(campaign=campaign).annotate(
            total_responses=Count('responses'),
            avg_duration=Avg('responses__duration'),
            avg_prep_time=Avg('responses__preparation_time_used')
        ).values('id', 'text', 'total_responses', 'avg_duration', 'avg_prep_time')
    
    def get_candidate_performance(self, campaign):
        return Candidate.objects.filter(
            interviews__campaign=campaign,
            interviews__responses__evaluation__isnull=False
        ).annotate(
            avg_score=Avg('interviews__responses__evaluation__overall_score'),
            total_evaluated=Count('interviews__responses__evaluation')
        ).values('id', 'first_name', 'last_name', 'avg_score', 'total_evaluated')

class CampaignShareViewSet(viewsets.ModelViewSet):
    """Gestion du partage de campagnes"""
    serializer_class = CampaignShareSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        hiring_manager = HiringManager.objects.get(
            user_profile__user=self.request.user
        )
        return CampaignShare.objects.filter(
            Q(shared_by=hiring_manager) | Q(shared_with=hiring_manager)
        )
    
    def perform_create(self, serializer):
        hiring_manager = HiringManager.objects.get(
            user_profile__user=self.request.user
        )
        serializer.save(shared_by=hiring_manager)