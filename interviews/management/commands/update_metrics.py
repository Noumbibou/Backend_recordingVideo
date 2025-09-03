from django.core.management.base import BaseCommand
from django.utils import timezone
from interviews.models import DashboardMetrics, HiringManager

class Command(BaseCommand):
    help = 'Met à jour les métriques du tableau de bord recruteur'
    
    def handle(self, *args, **options):
        for manager in HiringManager.objects.all():
            metrics, created = DashboardMetrics.objects.get_or_create(
                hiring_manager=manager
            )
            
            # Métriques simples pour démarrer
            campaigns = manager.campaigns.all()
            metrics.total_campaigns = campaigns.count()
            metrics.active_campaigns = campaigns.filter(
                is_active=True,
                end_date__gte=timezone.now()
            ).count()
            
            # On initialise à 0, on complétera plus tard
            metrics.total_candidates = 0
            metrics.completed_interviews = 0
            metrics.average_rating = 0.0
            
            metrics.save()
            
        self.stdout.write(self.style.SUCCESS('Métriques de base mises à jour avec succès'))