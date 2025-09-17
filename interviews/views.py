from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from django.utils import timezone
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
import logging

from .models import (
    HiringManager, UserProfile, VideoCampaign, Question, Candidate,
    InterviewSession, VideoResponse, SessionLog, AIAnalysis,
    VideoSettings, DashboardMetrics, Evaluation, CampaignShare
)
from .serializers import (
    UserSerializer, HiringManagerSerializer, VideoCampaignSerializer,
    QuestionSerializer, CandidateSerializer, InterviewSessionSerializer,
    VideoResponseSerializer, SessionLogSerializer, AIAnalysisSerializer,
    VideoSettingsSerializer, DashboardMetricsSerializer,
    EvaluationSerializer, CampaignShareSerializer,
    CreateCampaignSerializer, InviteCandidateSerializer,
    StartSessionSerializer, SubmitVideoResponseSerializer,
    VideoUploadSerializer, CampaignStatsSerializer, StartInterviewSerializer
)

# -------------------------------
# AUTHENTIFICATION & REGISTER
# -------------------------------

User = get_user_model()
class RegisterView(generics.CreateAPIView):
    """
    Création d'un utilisateur avec rôle candidat ou recruteur.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        user_type = request.data.get('user_type')  # "candidate" ou "hiring_manager"

        # Vérification des champs obligatoires
        if not all([username, email, password, user_type]):
            return Response({"error": "Tous les champs (username, email, password, user_type) sont requis."},
                            status=status.HTTP_400_BAD_REQUEST)

        if user_type not in ['candidate', 'hiring_manager']:
            return Response({"error": "user_type doit être 'candidate' ou 'hiring_manager'."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Créer l'utilisateur Django
        user = User.objects.create_user(username=username, email=email, password=password)

        # Créer le profil utilisateur
        profile = UserProfile.objects.create(
            user=user,
            user_type=user_type
        )

        response_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "user_type": user_type
        }

        # Si candidat
        if user_type == 'candidate':
            # Tous les champs obligatoires côté candidat
            first_name = request.data.get('first_name')
            last_name = request.data.get('last_name')
            phone = request.data.get('phone')
            linkedin_url = request.data.get('linkedin_url', '')

            if not all([first_name, last_name, phone]):
                return Response({"error": "first_name, last_name et phone sont obligatoires pour un candidat."},
                                status=status.HTTP_400_BAD_REQUEST)

            Candidate.objects.create(
                user_profile=profile,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                linkedin_url=linkedin_url
            )

        # Si recruteur
        if user_type == 'hiring_manager':
            company = request.data.get('company')
            department = request.data.get('department')
            phone = request.data.get('phone')

            if not all([company, department, phone]):
                return Response({"error": "company, department et phone sont obligatoires pour un recruteur."},
                                status=status.HTTP_400_BAD_REQUEST)

            HiringManager.objects.create(
                user_profile=profile,
                company=company,
                department=department,
                phone=phone
            )

        return Response({"message": f"Compte {user_type} créé avec succès", "user": response_data},
                        status=status.HTTP_201_CREATED)


class UnifiedLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Accepte un identifiant qui peut être un email ou un username
        identifier = request.data.get("email") or request.data.get("username")
        password = request.data.get("password")

        if not identifier or not password:
            return Response({"error": "Identifiant et mot de passe requis"}, status=status.HTTP_400_BAD_REQUEST)

        # Trouver l'utilisateur par email OU username
        user = None
        # D'abord tenter par email exact
        user = User.objects.filter(email=identifier).first()
        if not user:
            # Sinon tenter par username
            user = User.objects.filter(username=identifier).first()
        if not user:
            return Response({"error": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        # Authentification via username (Django auth attend le username)
        user = authenticate(username=user.username, password=password)
        if not user:
            return Response({"error": "Mot de passe incorrect"}, status=status.HTTP_401_UNAUTHORIZED)

        profile = user.profile  # OneToOneField avec related_name='profile'

        # Génération des tokens JWT
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Récupération des infos utilisateur
        if profile.user_type == 'hiring_manager':
            hm = profile.hiring_manager
            data = {
                "role": "hiring_manager",
                "username": user.username,
                "company": hm.company,
            }
        elif profile.user_type == 'candidate':
            data = {
                "role": "candidate",
                "username": user.username,
                "email": profile.user.email,
            }
        else:
            data = {
                "role": "admin",
                "username": user.username
            }

        # Ajouter les tokens à la réponse
        data.update({
            "access_token": access_token,
            "refresh_token": refresh_token
        })

        return Response(data, status=status.HTTP_200_OK)


# -------------------------------
# VIEWSETS PRINCIPAUX
# -------------------------------

class HiringManagerViewSet(viewsets.ModelViewSet):
    queryset = HiringManager.objects.all()
    serializer_class = HiringManagerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Fix: HiringManager n'a pas de champ `user`, il est relié via user_profile.user
        return HiringManager.objects.filter(user_profile__user=self.request.user)
    
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        try:
            manager = request.user.profile.hiring_manager
        except Exception:
            return Response({"error": "No hiring manager profile found for user"}, status=status.HTTP_404_NOT_FOUND)

        campaigns = VideoCampaign.objects.filter(hiring_manager=manager)
        candidate_count = Candidate.objects.filter(interviews__campaign__in=campaigns).distinct().count()
        metrics = {
            "total_campaigns": campaigns.count(),
            "total_candidates": candidate_count,
            "completed_interviews": InterviewSession.objects.filter(
                campaign__in=campaigns, status="completed"
            ).count(),
        }
        return Response(metrics)

class VideoCampaignViewSet(viewsets.ModelViewSet):
    queryset = VideoCampaign.objects.all()
    serializer_class = VideoCampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VideoCampaign.objects.filter(hiring_manager__user_profile__user=user)
        # Auto-deactivate expired campaigns at query time
        try:
            now = timezone.now()
            VideoCampaign.objects.filter(end_date__lt=now, is_active=True).update(is_active=False)
        except Exception:
            pass
        # Optional filter by activity
        is_active_param = self.request.query_params.get('is_active')
        if is_active_param is not None:
            val = str(is_active_param).lower() in ['1', 'true', 'yes']
            qs = qs.filter(is_active=val)
        return qs
    
    # Utiliser le serializer de création pour POST/PUT, sinon le serializer standard pour GET
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateCampaignSerializer
        return VideoCampaignSerializer
    
    # Le serializer gère déjà l'enregistrement du recruteur
    def perform_create(self, serializer):
        serializer.save()  

    # Inviter un candidat à une campagne
    
    @action(detail=True, methods=["post"], url_path="invite-candidate")
    def invite_candidate(self, request, pk=None):
        campaign = self.get_object()
        # Interdire l'invitation si la campagne est expirée ou inactive
        now = timezone.now()
        if campaign.end_date < now or not campaign.is_active:
            return Response(
                {"error": "La campagne est expirée ou inactive. L'invitation est impossible."},
                status=status.HTTP_400_BAD_REQUEST
            )

        candidate_id = request.data.get("candidate_id")
        email = request.data.get("email")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        phone = request.data.get("phone", "")
        linkedin_url = request.data.get("linkedin_url", "")

        if candidate_id:
            # Cas candidat existant par id
            candidate = get_object_or_404(Candidate, id=candidate_id)
        elif email:
            # Si email fourni, tenter de récupérer le candidat existant
            candidate = Candidate.objects.filter(email=email).first()
            if not candidate:
                # Si le candidat n'existe pas, require first_name + last_name pour créer
                if not all([first_name, last_name]):
                    return Response(
                        {"error": "Le candidat n'existe pas. Fournissez first_name et last_name pour créer un nouveau candidat."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Créer un User “dummy” pour le candidat
                user = User.objects.create(username=email, email=email)
                user_profile = UserProfile.objects.create(user=user, user_type='candidate')

                # Créer le candidat
                candidate = Candidate.objects.create(
                    user_profile=user_profile,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    linkedin_url=linkedin_url
                )
        else:
            return Response(
                {"error": "Vous devez fournir candidate_id ou email (si candidat existant) ou email + first_name + last_name (pour création)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer la session d’entretien
        session = InterviewSession.objects.create(
            campaign=campaign,
            candidate=candidate,
            expires_at=campaign.end_date
        )

        session_data = InterviewSessionSerializer(session, context={"request": request}).data
        response_payload = {
            "access_token": str(session.access_token),
            "expires_at": session.expires_at.isoformat(),
            "session": session_data
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["get"], url_path="sessions")
    def list_sessions(self, request, pk=None):
        campaign = self.get_object()

        # Vérifier droit d'accès : le recruteur propriétaire
        if campaign.hiring_manager.user_profile.user != request.user:
            raise PermissionDenied("Accès refusé à ces sessions.")

        sessions_qs = campaign.sessions.select_related('candidate', 'campaign').prefetch_related('responses__evaluations', 'responses__ai_analysis', 'campaign__questions')

        data = []
        now = timezone.now()
        for s in sessions_qs:
            # Auto-cancel strictly per business rule
            if s.status not in ["completed", "cancelled"] and _should_cancel(s, now):
                s.status = "cancelled"
                try:
                    s.save(update_fields=["status"])
                except Exception:
                    pass
            candidate = s.candidate
            responses = []
            for r in s.responses.all():
                # résumé des évaluations
                evals = []
                for ev in r.evaluations.all():
                    evals.append({
                        "id": ev.id,
                        "hiring_manager_id": ev.hiring_manager.id,
                        "technical_skill": ev.technical_skill,
                        "communication": ev.communication,
                        "motivation": ev.motivation,
                        "cultural_fit": ev.cultural_fit,
                        "notes": ev.notes,
                        "recommended": ev.recommended,
                        "evaluated_at": ev.evaluated_at,
                        "overall_score": ev.overall_score
                    })
                ai = None
                if hasattr(r, 'ai_analysis'):
                    ai = {
                        "speech_confidence": r.ai_analysis.speech_confidence,
                        "speech_rate": r.ai_analysis.speech_rate,
                        "sentiment_score": r.ai_analysis.sentiment_score,
                        "analyzed_at": r.ai_analysis.analyzed_at
                    }
                responses.append({
                    "id": str(r.id),
                    "question_id": r.question.id,
                    "question_order": r.question.order,
                    "video_url": r.video_url or r.video_file.url,
                    "duration": r.duration,
                    "upload_status": r.upload_status,
                    "recorded_at": r.recorded_at,
                    "file_size": r.file_size,
                    "format": r.format,
                    "evaluations": evals,
                    "ai_analysis": ai
                })

            data.append({
                "id": str(s.id),
                "status": s.status,
                "candidate": {
                    "id": str(candidate.id),
                    "email": candidate.email,
                    "first_name": candidate.first_name,
                    "last_name": candidate.last_name
                },
                "responses_count": s.responses.count(),
                "responses": responses,
                "invited_at": s.invited_at,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            })

        return Response({"sessions": data})    


    
class InterviewSessionViewSet(viewsets.ModelViewSet):
    queryset = InterviewSession.objects.all()
    serializer_class = InterviewSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Filtrage basé sur le rôle de l'utilisateur
        user = self.request.user
        queryset = InterviewSession.objects.all()
        
        if hasattr(user, 'profile') and hasattr(user.profile, 'hiring_manager'):
            queryset = queryset.filter(campaign__hiring_manager=user.profile.hiring_manager)
        else:
            return InterviewSession.objects.none()
            
        # Optimisation du chargement des relations
        queryset = queryset.select_related('candidate', 'campaign')
        queryset = queryset.prefetch_related(
            'responses__evaluations',
            'responses__question',
            'logs'
        )
        # Optional filters
        candidate_email = self.request.query_params.get('candidate_email')
        if candidate_email:
            queryset = queryset.filter(candidate__email__iexact=candidate_email)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Auto-cancel pass (side-effect) to keep status fresh when recruiter fetches sessions
        try:
            now = timezone.now()
            for s in queryset:
                if s.status not in ["completed", "cancelled"] and _should_cancel(s, now):
                    s.status = "cancelled"
                    s.save(update_fields=["status"])
        except Exception:
            pass

        # Order newest first so recent sessions appear on page 1
        return queryset.order_by('-invited_at')
    
    def get_serializer_context(self):
        # Ajout de la requête au contexte du sérialiseur
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=["post"], url_path="start")
    def start_session(self, request, pk=None):
        session = self.get_object()
        session.status = "in_progress"
        session.started_at = timezone.now()
        session.save()
        return Response({"message": "Session démarrée"})

    @action(detail=True, methods=["post"], url_path="submit-response")
    def submit_response(self, request, pk=None):
        session = self.get_object()
        serializer = SubmitVideoResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        VideoResponse.objects.create(session=session, **serializer.validated_data)
        return Response({"message": "Réponse enregistrée"})


class EvaluationViewSet(viewsets.ModelViewSet):
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        """Ajoute la requête au contexte du sérialiseur."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        # Ne retourner que les évaluations du recruteur connecté
        return Evaluation.objects.filter(
            hiring_manager__user_profile__user=self.request.user
        )

    def create(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        logger.info("=== NOUVELLE DEMANDE D'ÉVALUATION ===")
        logger.info(f"Méthode: {request.method}")
        logger.info(f"Utilisateur: {request.user} (ID: {request.user.id})")
        logger.info(f"Données reçues: {request.data}")
        
        try:
            # Vérifier que l'utilisateur est un recruteur
            try:
                hiring_manager = request.user.profile.hiring_manager
                logger.info(f"Hiring manager trouvé: {hiring_manager}")
            except AttributeError as e:
                error_msg = "L'utilisateur n'est pas un recruteur"
                logger.error(f"{error_msg}: {e}")
                return Response(
                    {"detail": error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Utiliser le sérialiseur pour valider les données
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Données invalides: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier que la réponse vidéo existe
            video_response_id = request.data.get('video_response')
            try:
                video_response = VideoResponse.objects.get(id=video_response_id)
                logger.info(f"Réponse vidéo trouvée: {video_response}")
            except VideoResponse.DoesNotExist:
                error_msg = f"Réponse vidéo introuvable avec l'ID: {video_response_id}"
                logger.error(error_msg)
                return Response(
                    {"video_response": [error_msg]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier que le recruteur a accès à cette réponse vidéo
            if video_response.session.campaign.hiring_manager != hiring_manager:
                error_msg = "Vous n'avez pas la permission d'évaluer cette réponse."
                logger.warning(f"Accès refusé - {error_msg}")
                return Response(
                    {"detail": error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Bloquer l'évaluation si la session est annulée ou expirée
            session_status = getattr(video_response.session, 'status', '').lower()
            if session_status in ["cancelled", "expired"]:
                error_msg = "Évaluation impossible: la session est annulée ou expirée."
                logger.warning(error_msg)
                return Response({"detail": error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier qu'il n'existe pas déjà une évaluation pour cette réponse
            if Evaluation.objects.filter(
                video_response=video_response,
                hiring_manager=hiring_manager
            ).exists():
                error_msg = "Une évaluation existe déjà pour cette réponse."
                logger.warning(error_msg)
                return Response(
                    {"detail": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Créer l'évaluation
            try:
                evaluation = serializer.save()
                logger.info(f"Évaluation créée avec succès - ID: {evaluation.id}")
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data, 
                    status=status.HTTP_201_CREATED, 
                    headers=headers
                )
                
            except Exception as e:
                error_msg = f"Erreur lors de la création de l'évaluation: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return Response(
                    {"detail": "Une erreur est survenue lors de la création de l'évaluation."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Response(
                {"detail": "Une erreur est survenue lors du traitement de la demande."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        logger.info("=== MISE À JOUR D'ÉVALUATION ===")
        logger.info(f"Utilisateur: {request.user} (ID: {request.user.id})")
        logger.info(f"Données reçues: {request.data}")
        
        try:
            instance = self.get_object()
            
            # Vérifier que l'utilisateur est le propriétaire de l'évaluation
            if instance.hiring_manager.user_profile.user != request.user:
                error_msg = "Vous n'avez pas la permission de modifier cette évaluation."
                logger.warning(error_msg)
                return Response(
                    {"detail": error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Bloquer la modification si la session liée est annulée ou expirée
            try:
                session_status = getattr(instance.video_response.session, 'status', '').lower()
                if session_status in ["cancelled", "expired"]:
                    error_msg = "Modification impossible: la session est annulée ou expirée."
                    logger.warning(error_msg)
                    return Response({"detail": error_msg}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass

            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
            if not serializer.is_valid():
                logger.warning(f"Données invalides: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            self.perform_update(serializer)
            logger.info(f"Évaluation mise à jour avec succès - ID: {instance.id}")
            return Response(serializer.data)
            
        except Exception as e:
            error_msg = f"Erreur lors de la mise à jour de l'évaluation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Response(
                {"detail": "Une erreur est survenue lors de la mise à jour de l'évaluation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_update(self, serializer):
        logger = logging.getLogger(__name__)
        try:
            serializer.save()
            logger.info("Mise à jour de l'évaluation effectuée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de la mise à jour: {str(e)}", exc_info=True)
            raise


class CampaignShareViewSet(viewsets.ModelViewSet):
    queryset = CampaignShare.objects.all()
    serializer_class = CampaignShareSerializer
    permission_classes = [permissions.IsAuthenticated]


# -------------------------------
# DASHBOARD & ANALYTICS
# -------------------------------

class RecruiterDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Récupérer le HiringManager via le profil lié à l'utilisateur
        try:
            manager = request.user.profile.hiring_manager
        except Exception:
            return Response({"error": "No hiring manager profile found for user"}, status=status.HTTP_404_NOT_FOUND)

        campaigns = VideoCampaign.objects.filter(hiring_manager=manager)
        # candidates count limité aux candidats liés aux sessions de ces campagnes
        candidate_count = Candidate.objects.filter(interviews__campaign__in=campaigns).distinct().count()
        metrics = {
            "total_campaigns": campaigns.count(),
            "total_candidates": candidate_count,
            "completed_interviews": InterviewSession.objects.filter(
                campaign__in=campaigns, status="completed"
            ).count(),
        }
        return Response(metrics)


class CampaignAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, campaign_id):
        campaign = get_object_or_404(VideoCampaign, id=campaign_id)
        sessions = InterviewSession.objects.filter(campaign=campaign)

        stats = {
            "total_candidates": sessions.count(),
            "completed": sessions.filter(status="completed").count(),
            "average_score": Evaluation.objects.filter(
                video_response__session__campaign=campaign
            ).aggregate(Avg("overall_score"))["overall_score__avg"]
        }
        return Response(stats)


# -------------------------------
# EXTRA VUES
# -------------------------------
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.conf import settings
from django.db import transaction
import os
import logging
import json
from datetime import timedelta

logger = logging.getLogger(__name__)

def _is_link_invalid(session, now):
    """Return True if the candidate link is no longer valid."""
    try:
        # Link is considered invalid once the session has been used to start the interview
        if getattr(session, 'is_used', False):
            return True
        if session.expires_at and session.expires_at < now:
            return True
    except Exception:
        pass
    try:
        campaign = session.campaign
        if campaign.end_date and campaign.end_date < now:
            return True
        # if campaign explicitly inactive
        if hasattr(campaign, 'is_active') and campaign.is_active is False:
            return True
    except Exception:
        pass
    return False

def _is_incomplete(session):
    """Return True if the session has NOT submitted all required responses.
    If no required questions are flagged, consider all campaign questions as required.
    """
    try:
        campaign = session.campaign
        required_qs = campaign.questions.filter(is_required=True)
        if not required_qs.exists():
            required_qs = campaign.questions.all()
        required_ids = set(required_qs.values_list('id', flat=True))
        if not required_ids:
            # no questions at all -> consider incomplete until completed explicitly
            return True
        answered_q_ids = set(session.responses.values_list('question_id', flat=True))
        return not required_ids.issubset(answered_q_ids)
    except Exception:
        # Be safe and consider it incomplete if we cannot compute properly
        return True

def _should_cancel(session, now):
    """Business rule: cancel only when candidate has started and didn't finish,
    and the link is no longer valid.
    Started means status in ["started", "in_progress"].
    """
    try:
        if session.status not in ["started", "in_progress"]:
            return False
        return _is_link_invalid(session, now) and _is_incomplete(session)
    except Exception:
        return False

class StartInterviewView(APIView):
    """
    Marque la session comme démarrée et invalide le lien
    """
    permission_classes = []
    serializer_class = StartInterviewSerializer
    
    def post(self, request, access_token):
        try:
            session = InterviewSession.objects.get(access_token=access_token)
            
            # Vérifications de sécurité
            if session.status != "invited" or session.is_used:
                return Response(
                    {"error": "Cette session a déjà été utilisée ou n'est plus valide", "code": "session_invalid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if session.expires_at < timezone.now():
                session.is_used = True
                # Cancel if incomplete per business rule
                if _is_incomplete(session):
                    session.status = "cancelled"
                else:
                    session.status = "expired"
                session.save()
                return Response(
                    {"error": "Le lien a expiré", "code": "link_expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Invalider le lien
            session.status = "in_progress"
            session.is_used = True
            session.started_at = timezone.now()
            session.save()
            
            logger.info(f"Session {session.id} démarrée avec succès")
            
            # Utilisation du sérialiseur pour la réponse
            serializer = self.serializer_class({
                "session_id": session.id,
                "success": True
            })
            return Response(serializer.data)
            
        except InterviewSession.DoesNotExist:
            return Response(
                {"error": "Session introuvable", "code": "session_not_found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la session: {str(e)}", exc_info=True)
            return Response(
                {"error": "Erreur serveur lors du démarrage de la session", "code": "server_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CandidateSessionAccessView(APIView):
    """
    Gère l'accès des candidats à leur session via un lien unique.
    Le lien devient invalide dès que l'entretien commence.
    """
    permission_classes = []  # Pas besoin d'auth pour le candidat via lien

    def get(self, request, access_token):
        try:
            session = InterviewSession.objects.get(access_token=access_token)
        except InterviewSession.DoesNotExist:
            return Response(
                {"error": "Session introuvable", "code": "session_not_found"},
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.now()

        # Vérification de la validité (expiration session/campagne ou campagne inactive)
        if _is_link_invalid(session, now):
            session.is_used = True
            # Cancel if incomplete per business rule
            if _is_incomplete(session):
                session.status = "cancelled"
            else:
                session.status = "expired"
            session.save()
            return Response(
                {"error": "Ce lien a expiré", "code": "link_expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier si la session a déjà été démarrée
        if session.is_used or session.status != "invited":
            return Response(
                {"error": "La session a déjà été démarrée. Veuillez utiliser le même onglet/navigateur.",
                 "code": "session_already_started"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Préparer les questions
        questions = session.campaign.questions.all().order_by('order')
        questions_data = [
            {
                "id": str(q.id),
                "text": q.text,
                "order": q.order,
                "preparation_time": q.preparation_time,
                "response_time_limit": q.response_time_limit,
            }
            for q in questions
        ]

        response_data = {
            "success": True,
            "session_id": str(session.id),
            "campaign": {
                "id": str(session.campaign.id),
                "title": session.campaign.title,
                "description": session.campaign.description or "",
            },
            "questions": questions_data,
            "status": session.status,
            "is_used": session.is_used
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, access_token):
        """
        Démarrage de la session ou soumission d'une réponse vidéo.
        """
        session = get_object_or_404(InterviewSession, access_token=access_token)
        now = timezone.now()

        # Vérification de l'expiration
        if session.expires_at < now:
            session.is_used = True
            session.status = "expired"
            session.save()
            return Response(
                {"error": "Ce lien a expiré", "code": "link_expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier si c'est une demande de démarrage de session
        if request.data.get('action') == 'start_session':
            if session.status != "invited" or session.is_used:
                return Response(
                    {"error": "Session déjà démarrée ou invalide", "code": "session_invalid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Marquer la session comme démarrée
            session.status = "in_progress"
            session.is_used = True
            session.started_at = now
            session.save()
            
            return Response({
                "success": True, 
                "session_id": str(session.id),
                "status": session.status,
                "started_at": session.started_at
            })

        # Si ce n'est pas une demande de démarrage, vérifier si la session est valide
        if session.status not in ["in_progress"]:
            return Response(
                {"error": "Session non démarrée ou déjà terminée", "code": "session_invalid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Gestion de la soumission de réponse vidéo
        serializer = SubmitVideoResponseSerializer(data=request.data, context={'session': session})
        serializer.is_valid(raise_exception=True)
        video_response = serializer.save()

        # Log de la soumission
        SessionLog.objects.create(
            session=session,
            log_type="video_submitted",
            message=f"Réponse pour Q{video_response.question.order} soumise",
            timestamp=now,
            metadata={
                "question_id": str(video_response.question.id),
                "duration": video_response.duration
            }
        )

        # Mettre à jour le statut de la session
        if session.responses.count() >= session.campaign.questions.count():
            session.status = "completed"
            session.completed_at = now
            session.save()
            return Response({"success": True, "message": "Toutes les réponses ont été enregistrées. Merci pour votre participation !"})
        
        return Response({"success": True, "message": "Réponse enregistrée avec succès"})

class SubmitInterviewResponsesView(APIView):
    """
    Gère la soumission des réponses vidéo d'un entretien.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = []

    @transaction.atomic
    def post(self, request, session_id):
        try:
            session = InterviewSession.objects.get(id=session_id)
            
            if session.status != "in_progress":
                return Response(
                    {"error": "Cette session n'est pas en cours", "code": "invalid_session_status"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            responses = request.data.getlist('responses')
            if not responses:
                return Response(
                    {"error": "Aucune réponse fournie", "code": "no_responses"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Traiter chaque réponse
            for response_data in responses:
                try:
                    response_json = json.loads(response_data)
                    question_id = response_json.get('question_id')
                    # Front envoie en millisecondes -> convertir en secondes entières positives
                    preparation_time_ms = int(response_json.get('preparation_time', 0) or 0)
                    recording_time_ms = int(response_json.get('recording_time', 0) or 0)
                    preparation_time_used = max(0, preparation_time_ms // 1000)
                    response_time_used = max(0, recording_time_ms // 1000)
                    video_file = request.FILES.get(f"video_{question_id}")

                    if not video_file:
                        logger.warning("No video file found for question_id=%s", question_id)
                        continue

                    # Créer la réponse vidéo avec les bons champs du modèle
                    video_response = VideoResponse.objects.create(
                        session=session,
                        question_id=question_id,
                        video_file=video_file,
                        preparation_time_used=preparation_time_used,
                        response_time_used=response_time_used,
                        duration=response_time_used,
                        upload_status="completed",
                        file_size=getattr(video_file, 'size', 0),
                        format=(video_file.name.split('.')[-1].lower() if '.' in video_file.name else '')
                    )

                    # Journaliser la soumission
                    SessionLog.objects.create(
                        session=session,
                        log_type="video_submitted",
                        message=f"Réponse pour la question {question_id} soumise",
                        metadata={
                            "question_id": str(question_id),
                            "preparation_time_used": preparation_time_used,
                            "response_time_used": response_time_used,
                            "file_size": getattr(video_file, 'size', 0)
                        }
                    )

                except Exception as e:
                    logger.error("Erreur lors du traitement d'une réponse (question_id=%s): %s", question_id, str(e), exc_info=True)
                    # Propager l'erreur pour rollback de la transaction et informer le client
                    return Response({"error": "invalid_response_payload", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # Mettre à jour le statut de la session si toutes les réponses sont soumises
            if session.responses.count() >= session.campaign.questions.count():
                session.status = "completed"
                session.completed_at = timezone.now()
                session.save()

                # Journaliser la fin de la session
                SessionLog.objects.create(
                    session=session,
                    log_type="session_completed",
                    message="Toutes les réponses ont été soumises"
                )

            return Response({
                "success": True,
                "message": "Réponses enregistrées avec succès"
            })

        except InterviewSession.DoesNotExist:
            return Response(
                {"error": "Session introuvable", "code": "session_not_found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erreur lors de la soumission des réponses: {str(e)}", exc_info=True)
            return Response(
                {"error": "Erreur lors de l'enregistrement des réponses", "code": "server_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VideoSettingsViewSet(viewsets.ModelViewSet):
    queryset = VideoSettings.objects.all()
    serializer_class = VideoSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]


class DashboardMetricsViewSet(viewsets.ModelViewSet):
    queryset = DashboardMetrics.objects.all()
    serializer_class = DashboardMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]


class AIAnalysisViewSet(viewsets.ModelViewSet):
    queryset = AIAnalysis.objects.all()
    serializer_class = AIAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # On suppose que la question est rattachée à une campagne
        campaign_id = self.request.data.get("campaign")
        campaign = get_object_or_404(VideoCampaign, id=campaign_id)
        serializer.save(campaign=campaign)


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Si tu veux éviter les doublons email
        email = serializer.validated_data.get("email")
        if Candidate.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Ce candidat existe déjà"})
        serializer.save()


class VideoResponseViewSet(viewsets.ModelViewSet):
    queryset = VideoResponse.objects.all()
    serializer_class = VideoResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        session_id = self.request.data.get("session")
        question_id = self.request.data.get("question")
        session = get_object_or_404(InterviewSession, id=session_id)
        question = get_object_or_404(Question, id=question_id)
        serializer.save(session=session, question=question)

class SessionLogViewSet(viewsets.ModelViewSet):
    queryset = SessionLog.objects.all()
    serializer_class = SessionLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        session_id = self.request.data.get("session")
        session = get_object_or_404(InterviewSession, id=session_id)
        serializer.save(session=session)

import os
import boto3
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

class PresignUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Body JSON: { "campaign_id": "<uuid>", "session_id": "<uuid>", "filename": "response.mp4", "max_mb": 100 }
        Returns: presigned POST object for direct upload to S3.
        """
        body = request.data
        filename = body.get("filename")
        campaign_id = body.get("campaign_id")
        session_id = body.get("session_id")
        max_mb = int(body.get("max_mb", 200))

        if not filename or not campaign_id or not session_id:
            return Response({"detail": "campaign_id, session_id and filename required"}, status=status.HTTP_400_BAD_REQUEST)

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        region = getattr(settings, "AWS_REGION", None)

        key = f"responses/{campaign_id}/{session_id}/{filename}"

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=region
        )

        max_bytes = max_mb * 1024 * 1024
        conditions = [
            {"acl": "private"},
            ["content-length-range", 1, max_bytes]
        ]
        fields = {"acl": "private", "Content-Type": "video/mp4"}

        try:
            presigned = s3.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=3600
            )
        except Exception as e:
            return Response({"detail": "presign_failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"presign": presigned, "key": key})
