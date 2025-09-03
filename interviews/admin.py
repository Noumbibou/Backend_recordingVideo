from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import HiringManager, Candidate, VideoCampaign, Question, VideoResponse, InterviewSession, SessionLog, AIAnalysis, VideoSettings # etc.

admin.site.register(HiringManager)
admin.site.register(Candidate)
admin.site.register(VideoCampaign)
admin.site.register(Question)
admin.site.register(VideoResponse)
admin.site.register(InterviewSession)
admin.site.register(SessionLog)
admin.site.register(AIAnalysis)
admin.site.register(VideoSettings)