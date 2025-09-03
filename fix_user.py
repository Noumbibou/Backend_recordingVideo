#!/usr/bin/env python
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User

def check_and_fix_user():
    """Vérifier et corriger l'utilisateur Bidou"""
    try:
        # Vérifier si l'utilisateur existe
        user = User.objects.get(username='Bidou')
        print(f"✅ Utilisateur trouvé: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - Active: {user.is_active}")
        print(f"   - Staff: {user.is_staff}")
        print(f"   - Superuser: {user.is_superuser}")
        
        # Changer le mot de passe
        user.set_password('Bidou0204./')
        user.save()
        print("✅ Mot de passe mis à jour")
        
    except User.DoesNotExist:
        print("❌ Utilisateur 'Bidou' non trouvé")
        # Créer l'utilisateur
        user = User.objects.create_user(
            username='Bidou',
            email='richnel@gmail.com',
            password='Bidou0204./',
            first_name='Bidou',
            last_name='User'
        )
        print("✅ Utilisateur créé avec succès")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == '__main__':
    check_and_fix_user()







