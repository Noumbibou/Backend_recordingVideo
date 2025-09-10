from django.core.management.base import BaseCommand
from django.db.models import Prefetch
from interviews.models import HiringManager, DashboardMetrics, VideoCampaign, Candidate, InterviewSession, Evaluation

class Command(BaseCommand):
    help = "Compute and persist DashboardMetrics for all HiringManagers"

    def handle(self, *args, **options):
        managers = HiringManager.objects.all().prefetch_related(
            Prefetch('campaigns', queryset=VideoCampaign.objects.all())
        )
        for hm in managers:
            campaigns = list(hm.campaigns.all())
            campaign_ids = [c.id for c in campaigns]

            total_campaigns = len(campaigns)
            active_campaigns = sum(1 for c in campaigns if c.is_active)

            total_candidates = Candidate.objects.filter(interviews__campaign__in=campaign_ids).distinct().count()
            completed_interviews = InterviewSession.objects.filter(campaign__in=campaign_ids, status='completed').count()

            evals = Evaluation.objects.filter(video_response__session__campaign__in=campaign_ids).select_related('video_response')
            scores = [e.overall_score for e in evals if e.overall_score is not None]
            average_rating = float(sum(scores) / len(scores)) if scores else 0.0

            DashboardMetrics.objects.update_or_create(
                hiring_manager=hm,
                defaults={
                    'total_campaigns': total_campaigns,
                    'active_campaigns': active_campaigns,
                    'total_candidates': total_candidates,
                    'completed_interviews': completed_interviews,
                    'average_rating': average_rating
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Metrics updated for {hm}"))