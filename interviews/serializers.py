from rest_framework import serializers
from .models import (
    HiringManager, VideoCampaign, Question, Candidate, 
    InterviewSession, VideoResponse, SessionLog, AIAnalysis, 
    VideoSettings, DashboardMetrics, Evaluation, CampaignShare
)
from django.contrib.auth.models import User


# ----------------------------
# UTILISATEURS
# ----------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class HiringManagerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user_profile.user.id', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = HiringManager
        fields = ['id', 'user_id', 'user_name', 'company', 'department', 'phone', 'is_active', 'created_at']

    def get_user_name(self, obj):
        try:
            user = obj.user_profile.user
            full = user.get_full_name() or ""
            if full.strip():
                return full
            # fallback sur username puis email
            return getattr(user, 'username', '') or getattr(user, 'email', '') or ""
        except Exception:
            return ""

# ----------------------------
# CAMPAGNES & QUESTIONS
# ----------------------------
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'preparation_time', 'response_time_limit', 'is_required']


class VideoCampaignSerializer(serializers.ModelSerializer):
    hiring_manager = HiringManagerSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    sessions = serializers.SerializerMethodField()
    sessions_count = serializers.SerializerMethodField()
    class Meta:
        model = VideoCampaign
        fields = [
            'id', 'title', 'description', 'hiring_manager', 'questions',
            'preparation_time', 'response_time_limit', 'max_questions', 'allow_retry',
            'created_at', 'start_date', 'end_date', 'is_active',
            'total_questions', 'sessions', 'sessions_count'
        ]
        read_only_fields = ['created_at']

    def get_total_questions(self, obj):
        return obj.questions.count()
    
    def get_sessions_count(self, obj):
        return obj.sessions.count()

    def get_sessions(self, obj):
        # Retourne les sessions avec un résumé (id, status, candidate, responses_count)
        sessions = obj.sessions.select_related('candidate').all()
        result = []
        for s in sessions:
            candidate = s.candidate
            candidate_name = f"{candidate.first_name} {candidate.last_name}" if candidate else None
            result.append({
                "id": str(s.id),
                "status": s.status,
                "candidate_id": str(candidate.id) if candidate else None,
                "candidate_name": candidate_name,
                "responses_count": s.responses.count()
            })
        return result

# ----------------------------
# CANDIDATS
# ----------------------------
class CandidateSerializer(serializers.ModelSerializer):
    user_profile_id = serializers.IntegerField(source='user_profile.id', read_only=True)
    user_type = serializers.CharField(source='user_profile.user_type', read_only=True)
    username = serializers.CharField(source='user_profile.user.username', read_only=True)

    class Meta:
        model = Candidate
        fields = [
            'id', 'user_profile_id', 'user_type', 'username',
            'email', 'first_name', 'last_name', 'phone', 'linkedin_url', 'created_at'
        ]
        read_only_fields = ['created_at', 'user_profile_id', 'user_type', 'username']

# ----------------------------
# EVALUATIONS
# ----------------------------
class EvaluationSerializer(serializers.ModelSerializer):
    hiring_manager = serializers.PrimaryKeyRelatedField(read_only=True)
    candidate_name = serializers.SerializerMethodField()
    question_text = serializers.SerializerMethodField()
    campaign_title = serializers.SerializerMethodField()
    overall_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            'id', 'video_response', 'hiring_manager', 'technical_skill',
            'communication', 'motivation', 'cultural_fit', 'notes',
            'recommended', 'evaluated_at', 'candidate_name', 'question_text',
            'campaign_title', 'overall_score'
        ]
        read_only_fields = ['evaluated_at', 'overall_score']

    def validate_technical_skill(self, value):
        return self._validate_rating(value, 'technical_skill')

    def validate_communication(self, value):
        return self._validate_rating(value, 'communication')

    def validate_motivation(self, value):
        return self._validate_rating(value, 'motivation')

    def validate_cultural_fit(self, value):
        return self._validate_rating(value, 'cultural_fit')

    def _validate_rating(self, value, field_name):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError(f"{field_name} doit être entre 1 et 5.")
        return value

    def validate(self, data):
        rating_fields = ['technical_skill', 'communication', 'motivation', 'cultural_fit']
        if not any(field in data for field in rating_fields):
            raise serializers.ValidationError("Au moins un critère d'évaluation doit être renseigné.")
        return data

    def create(self, validated_data):
        hiring_manager = self.context['request'].user.profile.hiring_manager
        validated_data['hiring_manager'] = hiring_manager
        return super().create(validated_data)

    def get_candidate_name(self, obj):
        return f"{obj.video_response.session.candidate.first_name} {obj.video_response.session.candidate.last_name}"

    def get_question_text(self, obj):
        return obj.video_response.question.text

    def get_campaign_title(self, obj):
        return obj.video_response.session.campaign.title

# ----------------------------
# REPONSES VIDEO
# ----------------------------
class VideoResponseSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    video_url = serializers.SerializerMethodField()
    evaluations = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoResponse
        fields = [
            'id', 'question', 'video_file', 'video_url', 'duration',
            'recorded_at', 'preparation_time_used', 'response_time_used',
            'upload_status', 'file_size', 'format', 'evaluations'
        ]
        read_only_fields = [
            'id', 'question', 'duration', 'recorded_at',
            'preparation_time_used', 'response_time_used',
            'upload_status', 'file_size', 'format', 'evaluations'
        ]
    
    def get_video_url(self, obj):
        if obj.video_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.video_file.url)
            return obj.video_file.url
        return obj.video_url
        
    def get_evaluations(self, obj):
        from .serializers import EvaluationSerializer
        return EvaluationSerializer(
            obj.evaluations.all(), 
            many=True,
            context=self.context
        ).data

# ----------------------------
# LOGS & ANALYSES
# ----------------------------
class SessionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionLog
        fields = ['id', 'log_type', 'message', 'timestamp', 'metadata']


class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            'id', 'speech_confidence', 'speech_rate', 'filler_words_count',
            'eye_contact_score', 'posture_score', 'gesture_score',
            'sentiment_score', 'confidence_score', 'analyzed_at', 'analysis_version'
        ]


# ----------------------------
# SESSIONS
# ----------------------------
class InterviewSessionSerializer(serializers.ModelSerializer):
    campaign = VideoCampaignSerializer(read_only=True)
    candidate = CandidateSerializer(read_only=True)
    responses = VideoResponseSerializer(many=True, read_only=True)
    logs = SessionLogSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewSession
        fields = [
            'id', 'campaign', 'candidate', 'status', 'invited_at', 
            'started_at', 'completed_at', 'expires_at', 'access_token',
            'responses', 'logs'
        ]
        read_only_fields = ['invited_at', 'started_at', 'completed_at', 'access_token']


# ----------------------------
# CAMPAGNE - CRÉATION
# ----------------------------
class CreateCampaignSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = VideoCampaign
        fields = [
            'title', 'description',
            'preparation_time', 'response_time_limit',
            'max_questions', 'allow_retry', 'start_date', 'end_date', 'questions'
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        user = self.context['request'].user

        # Vérification que l'utilisateur est un recruteur
        user_profile = self.context['request'].user.profile

        if not hasattr(user_profile, 'hiring_manager'):
            raise serializers.ValidationError("L'utilisateur connecté n'est pas un recruteur.")

        hiring_manager = user_profile.hiring_manager
        campaign = VideoCampaign.objects.create(hiring_manager=hiring_manager, **validated_data)

        # Créer les questions et les lier à la campagne
        for question_data in questions_data:
            Question.objects.create(campaign=campaign, **question_data)

        return campaign

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        return data



# ----------------------------
# OPERATIONS SPECIFIQUES
# ----------------------------
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework import serializers

class InviteCandidateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    campaign_id = serializers.UUIDField()
    
    def validate_email(self, value):
        if not Candidate.objects.filter(email=value).exists():
            raise serializers.ValidationError("Aucun candidat trouvé avec cet email.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        candidate = Candidate.objects.get(email=validated_data['email'])
        campaign = VideoCampaign.objects.get(id=validated_data['campaign_id'])
        
        # Créer une session d'entretien (token UUID généré automatiquement)
        session = InterviewSession.objects.create(
            candidate=candidate,
            campaign=campaign,
            status='invited'
        )
        
        # Récupérer le token unique (UUID)
        access_token = str(session.access_token)

        # Construire l'URL d'invitation
        invitation_url = f"{request.scheme}://{request.get_host()}/interview/{access_token}"
        
        # Envoyer l'e-mail
        self.send_invitation_email(candidate, campaign, invitation_url)
        
        return {
            'status': 'success',
            'message': f'Invitation envoyée à {candidate.email}',
            'invitation_url': invitation_url,  # utile pour debug / frontend
        }
    
    def send_invitation_email(self, candidate, campaign, invitation_url):
        subject = f"Invitation à un entretien vidéo - {campaign.title}"
        html_message = render_to_string('emails/candidate_invitation.html', {
            'candidate': candidate,
            'campaign': campaign,
            'invitation_url': invitation_url,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.email],
            fail_silently=False,
        )



class StartSessionSerializer(serializers.Serializer):
    access_token = serializers.UUIDField()

class StartInterviewSerializer(serializers.Serializer):
    """
    Sérialiseur pour valider les requêtes de démarrage d'entretien.
    """
    session_id = serializers.UUIDField(read_only=True)
    success = serializers.BooleanField(read_only=True)


from rest_framework import serializers
from .models import VideoResponse, Question, InterviewSession

class SubmitVideoResponseSerializer(serializers.ModelSerializer):
    # optional metadata that client can provide when using external URL upload
    file_size = serializers.IntegerField(required=False, min_value=0)
    format = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = VideoResponse
        fields = [
            'question',
            'video_file',
            'video_url',  # ajout du champ URL
            'duration',
            'preparation_time_used',
            'response_time_used',
            'file_size',
            'format',
        ]

    def validate(self, data):
        session = self.context.get('session')
        if not session:
            raise serializers.ValidationError("Session invalide.")

        # Vérifier que la question fait partie de la campagne
        question = data.get('question')
        if question is None:
            raise serializers.ValidationError("La question est requise.")
        if question.campaign != session.campaign:
            raise serializers.ValidationError("La question ne fait pas partie de cette campagne.")

        # Vérifier qu'au moins video_file ou video_url est fourni
        video_file = data.get('video_file', None)
        video_url = data.get('video_url', None)
        if not video_file and not video_url:
            raise serializers.ValidationError("Vous devez fournir un fichier ou un lien vidéo.")

        # Récupérer les contraintes de la campagne (si présentes)
        video_settings = getattr(session.campaign, 'video_settings', None)
        max_mb = getattr(video_settings, 'max_video_size', None)
        allowed_formats = getattr(video_settings, 'allowed_formats', None) or []

        # Helper pour extraire extension
        def _ext_from_name(name):
            try:
                return name.rsplit('.', 1)[-1].lower()
            except Exception:
                return ''

        # Validation pour upload direct (video_file)
        if video_file:
            size_bytes = getattr(video_file, 'size', None)
            if size_bytes is not None and max_mb is not None:
                size_mb = size_bytes / (1024 * 1024)
                if size_mb > max_mb:
                    raise serializers.ValidationError(f"Fichier trop volumineux ({size_mb:.1f}MB) — limite {max_mb}MB.")

            name = getattr(video_file, 'name', '')
            ext = _ext_from_name(name)
            if allowed_formats and ext not in [f.lower().lstrip('.') for f in allowed_formats]:
                raise serializers.ValidationError(f"Format '{ext}' non autorisé. Formats autorisés: {allowed_formats}.")

            # injecter métadonnées calculées
            data['file_size'] = size_bytes or data.get('file_size', 0)
            data['format'] = ext

        # Validation pour URL-based upload
        if video_url and not video_file:
            # prefer client-provided file_size/format if available
            provided_size = data.get('file_size')
            provided_format = (data.get('format') or '').lower()
            if max_mb is not None and provided_size:
                size_mb = provided_size / (1024 * 1024)
                if size_mb > max_mb:
                    raise serializers.ValidationError(f"Fichier (URL) trop volumineux ({size_mb:.1f}MB) — limite {max_mb}MB.")
            # try to infer ext from url if not provided
            if not provided_format:
                ext = _ext_from_name(video_url.split('?')[0].split('/')[-1])
            else:
                ext = provided_format
            if allowed_formats and ext and ext not in [f.lower().lstrip('.') for f in allowed_formats]:
                raise serializers.ValidationError(f"Format '{ext}' non autorisé pour l'URL. Formats autorisés: {allowed_formats}.")
            data['format'] = ext
            if provided_size:
                data['file_size'] = provided_size

        return data

    def create(self, validated_data):
        session = self.context['session']
        # session and question are saved by the serializer fields
        return VideoResponse.objects.create(session=session, **validated_data)


class VideoUploadSerializer(serializers.Serializer):
    file_url = serializers.URLField()
    file_size = serializers.IntegerField(min_value=1)
    format = serializers.CharField(max_length=10)


class VideoSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoSettings
        fields = '__all__'

    def validate_max_video_size(self, value):
        # max raisonnable = 5000 MB (5GB) — ajuste selon ta politique
        if value <= 0:
            raise serializers.ValidationError("max_video_size must be > 0 (MB).")
        if value > 5000:
            raise serializers.ValidationError("max_video_size too large (limit 5000 MB).")
        return value

    def validate_allowed_formats(self, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise serializers.ValidationError("allowed_formats must be a non-empty list.")
        # normaliser en minuscules, sans points
        cleaned = [str(v).lower().lstrip('.') for v in value]
        return cleaned

# ----------------------------
# DASHBOARD & PARTAGES
# ----------------------------
class DashboardMetricsSerializer(serializers.ModelSerializer):
    hiring_manager_name = serializers.CharField(source='hiring_manager.user_profile.user.get_full_name', read_only=True)

    class Meta:
        model = DashboardMetrics
        fields = '__all__'
        read_only_fields = ['last_updated']


class CampaignStatsSerializer(serializers.Serializer):
    campaign_id = serializers.UUIDField()
    campaign_title = serializers.CharField()
    total_candidates = serializers.IntegerField()
    completed_interviews = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    average_duration = serializers.FloatField()
    average_rating = serializers.FloatField()


class CampaignShareSerializer(serializers.ModelSerializer):
    shared_by_name = serializers.CharField(source='shared_by.user_profile.user.get_full_name', read_only=True)
    shared_with_name = serializers.CharField(source='shared_with.user_profile.user.get_full_name', read_only=True)
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignShare
        fields = '__all__'
        read_only_fields = ['shared_at']
