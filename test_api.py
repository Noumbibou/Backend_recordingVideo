#!/usr/bin/env python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "Bidou"
PASSWORD = "Fnrw0204./"  # Remplacez par votre mot de passe

def get_token():
    """Obtenir un token JWT"""
    url = f"{BASE_URL}/api/token/"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Token obtenu avec succès")
            return token_data['access']
        else:
            print(f"❌ Erreur d'authentification: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return None

def test_api_endpoints(token):
    """Tester les endpoints de l'API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Récupérer le profil Hiring Manager
    print("\n🔍 Test 1: Profil Hiring Manager")
    response = requests.get(f"{BASE_URL}/api/hiring-managers/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Profil récupéré: {data}")
    else:
        print(f"❌ Erreur: {response.text}")
    
    # Test 2: Lister les campagnes
    print("\n🔍 Test 2: Liste des campagnes")
    response = requests.get(f"{BASE_URL}/api/campaigns/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Campagnes récupérées: {len(data)} campagnes")
    else:
        print(f"❌ Erreur: {response.text}")
    
    # Test 3: Créer une campagne de test
    print("\n🔍 Test 3: Créer une campagne")
    campaign_data = {
        "title": "Entretien Développeur Full-Stack",
        "description": "Entretien vidéo pour le poste de développeur full-stack",
        "preparation_time": 30,
        "response_time_limit": 120,
        "max_questions": 3,
        "allow_retry": False,
        "start_date": "2024-01-15T10:00:00Z",
        "end_date": "2024-02-15T18:00:00Z",
        "questions": [
            {
                "text": "Pouvez-vous vous présenter et expliquer votre parcours ?",
                "order": 1,
                "preparation_time": 30,
                "response_time_limit": 120,
                "is_required": True
            },
            {
                "text": "Quels sont vos projets techniques les plus significatifs ?",
                "order": 2,
                "preparation_time": 30,
                "response_time_limit": 180,
                "is_required": True
            },
            {
                "text": "Pourquoi souhaitez-vous rejoindre notre équipe ?",
                "order": 3,
                "preparation_time": 30,
                "response_time_limit": 120,
                "is_required": True
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/campaigns/", headers=headers, json=campaign_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        campaign_id = data['id']
        print(f"✅ Campagne créée avec l'ID: {campaign_id}")
        
        # Test 4: Inviter des candidats
        print("\n🔍 Test 4: Inviter des candidats")
        candidates_data = [
            {
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+33 6 12 34 56 78"
            },
            {
                "email": "jane.smith@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+33 6 98 76 54 32"
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/invite_candidates/",
            headers=headers,
            json=candidates_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            for candidate in data['invited_candidates']:
                print(f"   - {candidate['candidate']}: {candidate['invite_url']}")
        else:
            print(f"❌ Erreur: {response.text}")
            
    else:
        print(f"❌ Erreur: {response.text}")

def main():
    """Fonction principale"""
    print("🚀 Test de l'API JOBGATE Video Interview")
    print("=" * 50)
    
    # Obtenir le token
    token = get_token()
    if not token:
        print("❌ Impossible d'obtenir le token. Vérifiez vos identifiants.")
        return
    
    # Tester les endpoints
    test_api_endpoints(token)
    
    print("\n" + "=" * 50)
    print("✅ Tests terminés !")

if __name__ == "__main__":
    main()
