from rest_framework import serializers
from .models import (
    HiringManager, VideoCampaign, Question, Candidate, 
    InterviewSession, VideoResponse, SessionLog, AIAnalysis, 
    VideoSettings, DashboardMetrics, Evaluation, CampaignShare
)
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class HiringManagerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = HiringManager
        fields = ['id', 'user', 'company', 'department', 'phone', 'is_active', 'created_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'preparation_time', 'response_time_limit', 'is_required']

class VideoCampaignSerializer(serializers.ModelSerializer):
    hiring_manager = HiringManagerSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoCampaign
        fields = [
            'id', 'title', 'description', 'hiring_manager', 'questions',
            'preparation_time', 'response_time_limit', 'max_questions', 'allow_retry',
            'created_at', 'start_date', 'end_date', 'is_active',
            'total_candidates', 'completed_interviews', 'total_questions'
        ]
        read_only_fields = ['created_at', 'total_candidates', 'completed_interviews']
    
    def get_total_questions(self, obj):
        return obj.questions.count()

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'linkedin_url', 'created_at']

class VideoResponseSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    evaluated_by = HiringManagerSerializer(read_only=True)
    
    class Meta:
        model = VideoResponse
        fields = [
            'id', 'question', 'video_file', 'video_url', 'duration',
            'recorded_at', 'preparation_time_used', 'response_time_used',
            'score', 'notes', 'evaluated_by', 'evaluated_at'
        ]
        read_only_fields = ['recorded_at', 'evaluated_at']

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

class InterviewSessionSerializer(serializers.ModelSerializer):
    campaign = VideoCampaignSerializer(read_only=True)
    candidate = CandidateSerializer(read_only=True)
    responses = VideoResponseSerializer(many=True, read_only=True)
    logs = SessionLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = InterviewSession
        fields = [
            'id', 'campaign', 'candidate', 'status', 'invited_at', 
            'started_at', 'completed_at', 'expires_at', 'total_questions',
            'answered_questions', 'total_duration', 'access_token',
            'responses', 'logs'
        ]
        read_only_fields = ['invited_at', 'started_at', 'completed_at', 'access_token']

# Serializers pour les opérations spécifiques
class CreateCampaignSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)
    hiring_manager = serializers.PrimaryKeyRelatedField(
    queryset=HiringManager.objects.all(),
    default=serializers.CurrentUserDefault()  # Utilise l'utilisateur courant
    )
    class Meta:
        model = VideoCampaign
        fields = [
            'title', 'description', 'hiring_manager', 'preparation_time', 'response_time_limit',
            'max_questions', 'allow_retry', 'start_date', 'end_date', 'questions'
        ]
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        campaign = VideoCampaign.objects.create(**validated_data)
        
        for question_data in questions_data:
            Question.objects.create(campaign=campaign, **question_data)
        
        return campaign
    
    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        return data

class InviteCandidateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)

    def validate_email(self, value):
        if Candidate.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un candidat avec cet email existe déjà.")
        return value

class StartSessionSerializer(serializers.Serializer):
    access_token = serializers.UUIDField()

class SubmitVideoResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoResponse
        fields = [
            'video_file',   # upload binaire
            'video_url',    # ou bien URL
            'duration',
            'preparation_time_used',
            'response_time_used'
        ]

    def validate(self, data):
        """
        Oblige l'utilisateur à fournir soit un fichier, soit une URL.
        """
        if not data.get('video_file') and not data.get('video_url'):
            raise serializers.ValidationError("Vous devez fournir un fichier vidéo OU une URL.")
        
        if data.get('video_file') and data.get('video_url'):
            raise serializers.ValidationError("Fournissez uniquement un fichier OU une URL, pas les deux.")
        
        return data



class VideoUploadSerializer(serializers.Serializer):
    file_url = serializers.URLField()
    file_size = serializers.IntegerField(min_value=1)
    format = serializers.CharField(max_length=10)

class VideoSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoSettings
        fields = '__all__'


#serializers pour les evaluations

class EvaluationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    question_text = serializers.SerializerMethodField()
    campaign_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Evaluation
        fields = [
            'id', 'video_response', 'hiring_manager', 'technical_skill',
            'communication', 'motivation', 'cultural_fit', 'notes',
            'recommended', 'evaluated_at', 'candidate_name', 'question_text',
            'campaign_title', 'overall_score'
        ]
        read_only_fields = ['evaluated_at', 'overall_score']
    
    def get_candidate_name(self, obj):
        return f"{obj.video_response.session.candidate.first_name} {obj.video_response.session.candidate.last_name}"
    
    def get_question_text(self, obj):
        return obj.video_response.question.text[:100] + "..." if len(obj.video_response.question.text) > 100 else obj.video_response.question.text
    
    def get_campaign_title(self, obj):
        return obj.video_response.session.campaign.title

class DashboardMetricsSerializer(serializers.ModelSerializer):
    hiring_manager_name = serializers.CharField(source='hiring_manager.user_profile.user.get_full_name', read_only=True)
    
    class Meta:
        model = DashboardMetrics
        fields = '__all__'
        read_only_fields = ['last_updated']

class CampaignStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques de campagne"""
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