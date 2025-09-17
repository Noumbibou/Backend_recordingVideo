from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

# ----------------------------
# PROFIL UTILISATEUR
# ----------------------------
class UserProfile(models.Model):
    """Profil étendu pour distinguer les rôles utilisateurs"""
    USER_TYPES = [
        ('hiring_manager', 'Recruteur'),
        ('candidate', 'Candidat'),
        ('admin', 'Administrateur'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='candidate')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"


class HiringManager(models.Model):
    """Recruteur / gestionnaire de campagnes"""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='hiring_manager')
    company = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.company}"


# ----------------------------
# CAMPAGNES & QUESTIONS
# ----------------------------
class VideoCampaign(models.Model):
    """Campagne d'entretien vidéo différé"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    hiring_manager = models.ForeignKey(HiringManager, on_delete=models.CASCADE, related_name='campaigns')
    
    # Config
    preparation_time = models.IntegerField(default=30)  # secondes
    response_time_limit = models.IntegerField(default=120)  # secondes
    max_questions = models.IntegerField(default=5)
    allow_retry = models.BooleanField(default=False)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("La date de fin doit être après la date de début.")
    
    def __str__(self):
        return f"{self.title} - {self.hiring_manager.company}"

    @property
    def is_expired(self):
        try:
            return self.end_date < timezone.now()
        except Exception:
            return False

    def save(self, *args, **kwargs):
        # Si la campagne est expirée, la marquer inactif automatiquement
        try:
            if self.end_date and self.end_date < timezone.now():
                self.is_active = False
        except Exception:
            pass
        super().save(*args, **kwargs)


class Question(models.Model):
    """Questions de l'entretien vidéo"""
    campaign = models.ForeignKey(VideoCampaign, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.IntegerField()
    preparation_time = models.IntegerField(default=30)
    response_time_limit = models.IntegerField(default=120)
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}..."


# ----------------------------
# CANDIDATS & SESSIONS
# ----------------------------
class Candidate(models.Model):
    """Infos candidat (lié à User si authentifié)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='candidate')
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    linkedin_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class InterviewSession(models.Model):
    """Session d'entretien d'un candidat"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(VideoCampaign, on_delete=models.CASCADE, related_name='sessions')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    
    STATUS_CHOICES = [
        ('invited', 'Invité'),
        ('started', 'Commencé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    
    invited_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)  # lien unique
    is_used = models.BooleanField(default=False)  # 🔒 une seule utilisation

    def __str__(self):
        return f"{self.candidate.email} - {self.campaign.title}"


# ----------------------------
# REPONSES VIDEO
# ----------------------------
class VideoSettings(models.Model):
    """Paramètres techniques de la campagne"""
    campaign = models.OneToOneField(VideoCampaign, on_delete=models.CASCADE, related_name='video_settings')
    max_video_size = models.IntegerField(default=500)  # MB
    enable_audio = models.BooleanField(default=True)
    enable_video = models.BooleanField(default=True)
    resolution = models.CharField(max_length=10, default='1280x720') 
    allowed_formats = models.JSONField(default=list)  # ex: ["webm", "mp4"]
    default_video_formats = ["mp4", "webm"] 


class VideoResponse(models.Model):
    """Réponse vidéo à une question"""
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    
    video_file = models.FileField(upload_to='video_responses/')
    video_url = models.URLField(blank=True)  # Cloud storage
    duration = models.IntegerField(default=0)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    preparation_time_used = models.IntegerField(default=0)
    response_time_used = models.IntegerField(default=0)
    
    upload_status = models.CharField(
        max_length=20,
        choices=[('uploading', 'En cours'), ('completed', 'Terminé'), ('failed', 'Échec')],
        default='uploading'
    )
    file_size = models.IntegerField(default=0)
    format = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.session.candidate.email} - Q{self.question.order}"


# ----------------------------
# EVALUATION & ANALYSE
# ----------------------------
class Evaluation(models.Model):
    """Évaluations multiples possibles sur une vidéo"""
    video_response = models.ForeignKey(VideoResponse, on_delete=models.CASCADE, related_name='evaluations')
    hiring_manager = models.ForeignKey(HiringManager, on_delete=models.CASCADE)
    
    RATING_CHOICES = [(i, f"{i}★") for i in range(1, 6)]
    technical_skill = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    communication = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    motivation = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    cultural_fit = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    recommended = models.BooleanField(null=True, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-evaluated_at']

    @property
    def overall_score(self):
        scores = [self.technical_skill, self.communication, self.motivation, self.cultural_fit]
        valid_scores = [s for s in scores if s is not None]
        return sum(valid_scores) / len(valid_scores) if valid_scores else None

    def __str__(self):
        return f"Évaluation {self.video_response} par {self.hiring_manager}"


class AIAnalysis(models.Model):
    """Analyse IA optionnelle d'une réponse vidéo"""
    video_response = models.OneToOneField(VideoResponse, on_delete=models.CASCADE, related_name='ai_analysis')
    
    speech_confidence = models.FloatField(null=True, blank=True)
    speech_rate = models.FloatField(null=True, blank=True)
    filler_words_count = models.IntegerField(default=0)
    
    eye_contact_score = models.FloatField(null=True, blank=True)
    posture_score = models.FloatField(null=True, blank=True)
    gesture_score = models.FloatField(null=True, blank=True)
    
    sentiment_score = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    analysis_version = models.CharField(max_length=20, default='1.0')
    
    def __str__(self):
        return f"Analyse IA - {self.video_response}"


# ----------------------------
# LOGS & METRIQUES
# ----------------------------
class SessionLog(models.Model):
    """Logs techniques de la session"""
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='logs')
    log_type = models.CharField(max_length=30)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']


class DashboardMetrics(models.Model):
    """Métriques pour tableau de bord recruteur"""
    hiring_manager = models.OneToOneField(HiringManager, on_delete=models.CASCADE)
    total_campaigns = models.IntegerField(default=0)
    active_campaigns = models.IntegerField(default=0)
    total_candidates = models.IntegerField(default=0)
    completed_interviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Métriques pour {self.hiring_manager}"


class CampaignShare(models.Model):
    """Partage de campagnes entre recruteurs"""
    campaign = models.ForeignKey(VideoCampaign, on_delete=models.CASCADE)
    shared_by = models.ForeignKey(HiringManager, on_delete=models.CASCADE, related_name='shared_campaigns')
    shared_with = models.ForeignKey(HiringManager, on_delete=models.CASCADE, related_name='received_campaigns')
    can_edit = models.BooleanField(default=False)
    can_view_responses = models.BooleanField(default=True)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['campaign', 'shared_with']

    def __str__(self):
        return f"{self.campaign} partagé avec {self.shared_with}"
