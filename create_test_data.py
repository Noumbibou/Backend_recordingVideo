#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from interviews.models import HiringManager, VideoCampaign, Question

def create_test_data():
    """Créer des données de test pour l'application"""
    
    # Créer un utilisateur de test
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Utilisateur créé: {user.username}")
    else:
        print(f"Utilisateur existant: {user.username}")
    
    # Créer un hiring manager
    hiring_manager, created = HiringManager.objects.get_or_create(
        user=user,
        defaults={
            'company': 'Test Company',
            'position': 'HR Manager'
        }
    )
    if created:
        print(f"Hiring Manager créé pour {user.username}")
    else:
        print(f"Hiring Manager existant pour {user.username}")
    
    # Créer des questions de test
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
    
    questions = []
    for q_data in questions_data:
        question, created = Question.objects.get_or_create(
            text=q_data['text'],
            defaults=q_data
        )
        questions.append(question)
        if created:
            print(f"Question créée: {question.text[:50]}...")
    
    # Créer une campagne de test
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
        # Ajouter les questions à la campagne
        campaign.questions.set(questions)
        print(f"Campagne créée: {campaign.title}")
    else:
        print(f"Campagne existante: {campaign.title}")
    
    # Créer une deuxième campagne
    campaign2, created = VideoCampaign.objects.get_or_create(
        title='Campagne de test - Chef de projet',
        defaults={
            'hiring_manager': hiring_manager,
            'description': 'Entretien pour un poste de chef de projet',
            'preparation_time': 45,
            'response_time_limit': 240,
            'max_questions': 2,
            'allow_retry': False,
            'start_date': datetime.now().date(),
            'end_date': (datetime.now() + timedelta(days=15)).date(),
            'is_active': True
        }
    )
    
    if created:
        # Ajouter seulement les 2 premières questions
        campaign2.questions.set(questions[:2])
        print(f"Campagne créée: {campaign2.title}")
    else:
        print(f"Campagne existante: {campaign2.title}")
    
    print("\n✅ Données de test créées avec succès!")
    print(f"📊 {VideoCampaign.objects.count()} campagnes disponibles")
    print(f"❓ {Question.objects.count()} questions disponibles")
    print(f"👤 {User.objects.count()} utilisateurs")

if __name__ == '__main__':
    create_test_data()


