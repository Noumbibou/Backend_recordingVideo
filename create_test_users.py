#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from interviews.models import UserProfile, HiringManager, VideoCampaign, Question, Candidate, InterviewSession

def create_test_users():
    """Créer des utilisateurs de test avec différents profils"""
    
    print("🔧 Création des utilisateurs de test...")
    
    # 1. Créer un recruteur
    recruiter_user, created = User.objects.get_or_create(
        username='recruiter',
        defaults={
            'email': 'recruiter@techcorp.com',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'is_active': True
        }
    )
    if created:
        recruiter_user.set_password('recruiter123')
        recruiter_user.save()
        print(f"✅ Recruteur créé: {recruiter_user.username}")
    else:
        print(f"ℹ️ Recruteur existant: {recruiter_user.username}")
    
    # Créer le profil recruteur
    recruiter_profile, created = UserProfile.objects.get_or_create(
        user=recruiter_user,
        defaults={'user_type': 'hiring_manager'}
    )
    if created:
        print(f"✅ Profil recruteur créé pour {recruiter_user.username}")
    
    # Créer le HiringManager
    hiring_manager, created = HiringManager.objects.get_or_create(
        user_profile=recruiter_profile,
        defaults={
            'company': 'TechCorp',
            'department': 'Ressources Humaines',
            'phone': '+33 1 23 45 67 89',
            'is_active': True
        }
    )
    if created:
        print(f"✅ HiringManager créé pour {recruiter_user.username}")
    
    # 2. Créer un candidat
    candidate_user, created = User.objects.get_or_create(
        username='candidate',
        defaults={
            'email': 'candidate@example.com',
            'first_name': 'Marie',
            'last_name': 'Martin',
            'is_active': True
        }
    )
    if created:
        candidate_user.set_password('candidate123')
        candidate_user.save()
        print(f"✅ Candidat créé: {candidate_user.username}")
    else:
        print(f"ℹ️ Candidat existant: {candidate_user.username}")
    
    # Créer le profil candidat
    candidate_profile, created = UserProfile.objects.get_or_create(
        user=candidate_user,
        defaults={'user_type': 'candidate'}
    )
    if created:
        print(f"✅ Profil candidat créé pour {candidate_user.username}")
    
    # Créer le Candidate
    candidate, created = Candidate.objects.get_or_create(
        email=candidate_user.email,
        defaults={
            'first_name': candidate_user.first_name,
            'last_name': candidate_user.last_name,
            'phone': '+33 6 12 34 56 78',
            'linkedin_url': 'https://linkedin.com/in/marie-martin'
        }
    )
    if created:
        print(f"✅ Candidate créé pour {candidate_user.username}")
    
    # 3. Créer des questions de test APRÈS la campagne
    questions_data = [
        {
            'text': 'Pouvez-vous vous présenter en 2 minutes ?',
            'order': 1,
            'preparation_time': 30,
            'response_time_limit': 120,
            'is_required': True
        },
        {
            'text': 'Quelle est votre plus grande réussite professionnelle ?',
            'order': 2,
            'preparation_time': 30,
            'response_time_limit': 180,
            'is_required': True
        },
        {
            'text': 'Pourquoi souhaitez-vous rejoindre notre entreprise ?',
            'order': 3,
            'preparation_time': 30,
            'response_time_limit': 150,
            'is_required': True
        }
    ]
    
    # 4. Créer des campagnes de test
    campaign, created = VideoCampaign.objects.get_or_create(
        title='Campagne de test - Développeur Full Stack',
        defaults={
            'hiring_manager': hiring_manager,
            'description': 'Entretien pour un poste de développeur full stack',
            'preparation_time': 30,
            'response_time_limit': 180,
            'max_questions': 3,
            'allow_retry': True,
            'start_date': datetime.now().date(),
            'end_date': (datetime.now() + timedelta(days=30)).date(),
            'is_active': True
        }
    )
    
    if created:
        print(f"✅ Campagne créée: {campaign.title}")
    
    # Maintenant créer les questions avec la campagne
    questions = []
    for q_data in questions_data:
        question, created = Question.objects.get_or_create(
            campaign=campaign,
            text=q_data['text'],
            defaults=q_data
        )
        questions.append(question)
        if created:
            print(f"✅ Question créée: {question.text[:50]}...")
    
    # 5. Créer une session d'entretien pour le candidat
    session, created = InterviewSession.objects.get_or_create(
        campaign=campaign,
        candidate=candidate,
        defaults={
            'status': 'invited',
            'expires_at': campaign.end_date,
            'total_questions': len(questions)
        }
    )
    if created:
        print(f"✅ Session d'entretien créée pour {candidate_user.username}")
    
    print("\n🎉 Utilisateurs de test créés avec succès!")
    print("\n📋 Informations de connexion:")
    print("=" * 50)
    print("👔 RECRUTEUR:")
    print(f"   Username: recruiter")
    print(f"   Password: recruiter123")
    print(f"   Email: {recruiter_user.email}")
    print(f"   Type: {recruiter_profile.get_user_type_display()}")
    print(f"   Entreprise: {hiring_manager.company}")
    print()
    print("👤 CANDIDAT:")
    print(f"   Username: candidate")
    print(f"   Password: candidate123")
    print(f"   Email: {candidate_user.email}")
    print(f"   Type: {candidate_profile.get_user_type_display()}")
    print(f"   LinkedIn: {candidate.linkedin_url}")
    print("=" * 50)
    print(f"\n📊 Statistiques:")
    print(f"   👥 Utilisateurs: {User.objects.count()}")
    print(f"   👔 Recruteurs: {UserProfile.objects.filter(user_type='hiring_manager').count()}")
    print(f"   👤 Candidats: {UserProfile.objects.filter(user_type='candidate').count()}")
    print(f"   📋 Campagnes: {VideoCampaign.objects.count()}")
    print(f"   ❓ Questions: {Question.objects.count()}")

if __name__ == '__main__':
    create_test_users()
