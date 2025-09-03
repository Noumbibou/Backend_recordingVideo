from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class UserProfile(models.Model):
    """Profil étendu de l'utilisateur pour distinguer les types"""
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
    
    @property
    def is_hiring_manager(self):
        return self.user_type == 'hiring_manager'
    
    @property
    def is_candidate(self):
        return self.user_type == 'candidate'

class HiringManager(models.Model):
    """Gestionnaire de recrutement avec droits restreints"""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='hiring_manager')
    company = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.company}"

class VideoCampaign(models.Model):
    """Campagne d'entretien vidéo différé"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    hiring_manager = models.ForeignKey(HiringManager, on_delete=models.CASCADE, related_name='campaigns')
    
    # Configuration de la campagne
    preparation_time = models.IntegerField(default=30)  # secondes
    response_time_limit = models.IntegerField(default=120)  # secondes
    max_questions = models.IntegerField(default=5)
    allow_retry = models.BooleanField(default=False)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Statistiques
    total_candidates = models.IntegerField(default=0)
    completed_interviews = models.IntegerField(default=0)

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("La date de fin doit être après la date de début.")
    
    def __str__(self):
        return f"{self.title} - {self.hiring_manager.company}"

class Question(models.Model):
    """Questions de l'entretien vidéo"""
    campaign = models.ForeignKey(VideoCampaign, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.IntegerField()
    preparation_time = models.IntegerField(default=30)  # secondes
    response_time_limit = models.IntegerField(default=120)  # secondes
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}..."

class Candidate(models.Model):
    """Candidat participant à l'entretien"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile', null=True, blank=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class InterviewSession(models.Model):
    """Session d'entretien pour un candidat"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(VideoCampaign, on_delete=models.CASCADE, related_name='sessions')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    
    # Statut de la session
    STATUS_CHOICES = [
        ('invited', 'Invité'),
        ('started', 'Commencé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    
    # Dates
    invited_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    # Statistiques
    total_questions = models.IntegerField(default=0)
    answered_questions = models.IntegerField(default=0)
    total_duration = models.IntegerField(default=0)  # secondes
    
    # Lien unique
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)
    
    def __str__(self):
        return f"{self.candidate.email} - {self.campaign.title}"

class VideoSettings(models.Model):
    campaign = models.OneToOneField(
        VideoCampaign, 
        on_delete=models.CASCADE,
        related_name='video_settings'
    )
    max_video_size = models.IntegerField(default=500)  # Taille max en MB
    enable_audio = models.BooleanField(default=True)
    enable_video = models.BooleanField(default=True)
    resolution = models.CharField(max_length=10, default='1280x720') 
    def default_video_formats():
        return ['webm', 'mp4']

    allowed_formats = models.JSONField(default=default_video_formats) # Résolution vidéo

class VideoResponse(models.Model):
    """Réponse vidéo à une question"""
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    
    # Fichier vidéo
    video_file = models.FileField(upload_to='video_responses/')
    video_url = models.URLField(blank=True)  # Pour stockage cloud
    duration = models.IntegerField(default=0)  # secondes
    
    # Métadonnées
    recorded_at = models.DateTimeField(auto_now_add=True)
    preparation_time_used = models.IntegerField(default=0)  # secondes
    response_time_used = models.IntegerField(default=0)  # secondes
    
    # Évaluation (optionnel)
    score = models.IntegerField(null=True, blank=True)  # 1-10
    notes = models.TextField(blank=True)
    evaluated_by = models.ForeignKey(HiringManager, on_delete=models.SET_NULL, null=True, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    upload_status = models.CharField(
        max_length=20,
        choices=[
            ('uploading', 'En cours'),
            ('completed', 'Terminé'),
            ('failed', 'Échec'),
        ],
        default='uploading'
    )
    file_size = models.IntegerField(default=0)  # Valeur par défaut # Nouveau champ
    format = models.CharField(max_length=10)  # Format vidéo (mp4, webm)
    
    def __str__(self):
        return f"{self.session.candidate.email} - Q{self.question.order}"

class SessionLog(models.Model):
    """Logs techniques de la session"""
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='logs')
    
    LOG_TYPES = [
        ('session_start', 'Début de session'),
        ('question_start', 'Début de question'),
        ('video_record', 'Enregistrement vidéo'),
        ('question_complete', 'Question terminée'),
        ('session_complete', 'Session terminée'),
        ('error', 'Erreur technique'),
        ('browser_close', 'Navigateur fermé'),
        ('microphone_error', 'Erreur microphone'),
        ('network_error', 'Erreur réseau'),
    ]
    
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)  # Données techniques
    
    class Meta:
        ordering = ['-timestamp']

class AIAnalysis(models.Model):
    """Analyse IA des réponses vidéo (optionnel)"""
    video_response = models.OneToOneField(VideoResponse, on_delete=models.CASCADE, related_name='ai_analysis')
    
    # Analyse vocale
    speech_confidence = models.FloatField(null=True, blank=True)  # 0-1
    speech_rate = models.FloatField(null=True, blank=True)  # mots/minute
    filler_words_count = models.IntegerField(default=0)
    
    # Analyse non verbale
    eye_contact_score = models.FloatField(null=True, blank=True)  # 0-1
    posture_score = models.FloatField(null=True, blank=True)  # 0-1
    gesture_score = models.FloatField(null=True, blank=True)  # 0-1
    
    # Sentiment
    sentiment_score = models.FloatField(null=True, blank=True)  # -1 à 1
    confidence_score = models.FloatField(null=True, blank=True)  # 0-1
    
    # Métadonnées
    analyzed_at = models.DateTimeField(auto_now_add=True)
    analysis_version = models.CharField(max_length=20, default='1.0')
    
    def __str__(self):
        return f"Analyse IA - {self.video_response}"


## Notes et évaluation

# Ajoutez ces classes à la fin de votre fichier models.py
class Evaluation(models.Model):
    """Système d'évaluation des réponses vidéo par les recruteurs"""
    video_response = models.OneToOneField('VideoResponse', on_delete=models.CASCADE, related_name='evaluation')
    hiring_manager = models.ForeignKey('HiringManager', on_delete=models.CASCADE)
    
    RATING_CHOICES = [
        (1, '★☆☆☆☆ - Insuffisant'),
        (2, '★★☆☆☆ - Moyen'),
        (3, '★★★☆☆ - Bon'),
        (4, '★★★★☆ - Très bon'),
        (5, '★★★★★ - Excellent')
    ]
    
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
        return f"Évaluation de {self.video_response} par {self.hiring_manager}"

class DashboardMetrics(models.Model):
    """Métriques pour le tableau de bord recruteur"""
    hiring_manager = models.OneToOneField('HiringManager', on_delete=models.CASCADE)
    total_campaigns = models.IntegerField(default=0)
    active_campaigns = models.IntegerField(default=0)
    total_candidates = models.IntegerField(default=0)
    completed_interviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Métriques pour {self.hiring_manager}"

class CampaignShare(models.Model):
    """Système de partage de campagnes entre recruteurs"""
    campaign = models.ForeignKey('VideoCampaign', on_delete=models.CASCADE)
    shared_by = models.ForeignKey('HiringManager', on_delete=models.CASCADE, related_name='shared_campaigns')
    shared_with = models.ForeignKey('HiringManager', on_delete=models.CASCADE, related_name='received_campaigns')
    can_edit = models.BooleanField(default=False)
    can_view_responses = models.BooleanField(default=True)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['campaign', 'shared_with']

    def __str__(self):
        return f"{self.campaign} partagé avec {self.shared_with}" 