# 🎥 Module d'Entretien Vidéo Différé - JOBGATE

## 📋 Architecture Générale

### **Stack Technologique**
- **Backend** : Django 4.2.7 + Django REST Framework
- **Base de données** : PostgreSQL
- **Frontend** : React.js + TypeScript
- **Authentification** : JWT (JSON Web Tokens)
- **Stockage vidéo** : AWS S3 (optionnel) ou stockage local
- **Analyse IA** : TensorFlow/PyTorch (optionnel)

## 🗄️ Structure de la Base de Données

### **Tables Principales**

#### 1. **HiringManager**
- Gestionnaires de recrutement avec droits restreints
- Lié à un utilisateur Django standard
- Informations de l'entreprise et département

#### 2. **VideoCampaign**
- Campagnes d'entretien vidéo différé
- Configuration : temps de préparation, durée de réponse, nombre max de questions
- Dates de début/fin et statistiques

#### 3. **Question**
- Questions de l'entretien avec ordre
- Temps de préparation et limite de réponse par question
- Option obligatoire/facultative

#### 4. **Candidate**
- Candidats participant aux entretiens
- Informations de contact et profil LinkedIn

#### 5. **InterviewSession**
- Sessions d'entretien pour chaque candidat
- Statut : invité, commencé, en cours, terminé, expiré
- Token d'accès unique et sécurisé

#### 6. **VideoResponse**
- Réponses vidéo aux questions
- Fichier vidéo, durée, métadonnées
- Évaluation par le recruteur (score, notes)

#### 7. **SessionLog**
- Logs techniques de la session
- Suivi des événements : début, erreurs, navigation
- Métadonnées pour debugging

#### 8. **AIAnalysis** (Optionnel)
- Analyse IA des réponses vidéo
- Métriques : confiance vocale, contact visuel, posture
- Scores de sentiment et confiance

## 🔌 API Endpoints

### **Authentification**
```
POST /api/token/          # Connexion JWT
POST /api/token/refresh/  # Rafraîchissement token
```

### **Hiring Managers**
```
GET    /api/hiring-managers/     # Profil du HM
PUT    /api/hiring-managers/{id}/ # Mise à jour profil
```

### **Campagnes**
```
GET    /api/campaigns/                    # Liste des campagnes
POST   /api/campaigns/                    # Créer une campagne
GET    /api/campaigns/{id}/               # Détails campagne
PUT    /api/campaigns/{id}/               # Modifier campagne
DELETE /api/campaigns/{id}/               # Supprimer campagne
POST   /api/campaigns/{id}/invite_candidates/ # Inviter candidats
GET    /api/campaigns/{id}/statistics/    # Statistiques
```

### **Sessions d'Entretien**
```
GET    /api/sessions/                     # Liste des sessions
GET    /api/sessions/{id}/                # Détails session
POST   /api/sessions/start_session/       # Démarrer session (candidat)
POST   /api/sessions/{id}/submit_response/ # Soumettre réponse
POST   /api/sessions/{id}/complete_session/ # Terminer session
```

### **Réponses Vidéo**
```
GET    /api/responses/                    # Liste des réponses
GET    /api/responses/{id}/               # Détails réponse
POST   /api/responses/{id}/evaluate/      # Évaluer réponse
```

### **Candidats**
```
GET    /api/candidates/                   # Liste des candidats
GET    /api/candidates/{id}/              # Détails candidat
```

### **Logs et Analyses**
```
GET    /api/logs/                         # Logs de session
GET    /api/ai-analysis/                  # Analyses IA
```

## 🎨 Interface Utilisateur

### **Interface Recruteur**

#### **Dashboard Principal**
- Vue d'ensemble des campagnes actives
- Statistiques en temps réel
- Notifications de nouvelles réponses

#### **Gestion des Campagnes**
- Création/modification de campagnes
- Configuration des questions
- Invitation de candidats
- Suivi des sessions

#### **Évaluation des Réponses**
- Lecteur vidéo intégré
- Système de notation (1-10)
- Commentaires et notes
- Comparaison entre candidats

### **Interface Candidat**

#### **Page d'Accueil**
- Introduction à l'entretien
- Instructions et conseils
- Test du microphone/caméra

#### **Interface d'Enregistrement**
- Prévisualisation webcam
- Minuteur de préparation
- Minuteur de réponse
- Contrôles d'enregistrement

#### **Navigation**
- Progression automatique entre questions
- Possibilité de revenir en arrière (si configuré)
- Confirmation avant soumission

## 🔒 Sécurité et Contraintes

### **Sécurité des Liens**
- Tokens UUID uniques et sécurisés
- Expiration automatique des sessions
- Validation côté serveur des accès

### **Contraintes Techniques**
- Une seule prise par question (sauf si configuré autrement)
- Détection de fermeture du navigateur
- Logs des erreurs techniques
- Validation des permissions

### **Gestion des Erreurs**
- Microphone non détecté
- Caméra non disponible
- Problèmes de réseau
- Navigateur non compatible

## 📱 Responsive Design

### **Desktop (≥1024px)**
- Interface complète avec sidebar
- Lecteur vidéo grand format
- Tableaux de données détaillés

### **Tablet (768px-1023px)**
- Interface adaptée avec navigation simplifiée
- Lecteur vidéo moyen format

### **Mobile (≤767px)**
- Interface optimisée pour tactile
- Lecteur vidéo plein écran
- Navigation par onglets

## 🚀 Plan de Développement Agile

### **Sprint 1 (2 semaines) - Fondations**
- [x] Structure de base de données
- [x] API REST de base
- [x] Authentification JWT
- [ ] Interface recruteur basique

### **Sprint 2 (2 semaines) - Enregistrement Vidéo**
- [ ] Interface candidat
- [ ] Enregistrement vidéo (MediaRecorder)
- [ ] Upload des fichiers
- [ ] Gestion des sessions

### **Sprint 3 (2 semaines) - Gestion des Campagnes**
- [ ] CRUD complet des campagnes
- [ ] Système d'invitation
- [ ] Dashboard recruteur
- [ ] Évaluation des réponses

### **Sprint 4 (2 semaines) - Optimisations**
- [ ] Interface responsive
- [ ] Gestion des erreurs
- [ ] Logs et monitoring
- [ ] Tests unitaires

### **Sprint 5 (2 semaines) - Fonctionnalités Avancées**
- [ ] Analyse IA (optionnel)
- [ ] Notifications email
- [ ] Export des données
- [ ] Documentation utilisateur

## 🔧 Configuration Technique

### **Variables d'Environnement**
```env
# Base de données
DB_NAME=video_interview_db
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=votre_clé_secrète
DEBUG=True

# Stockage vidéo (optionnel)
AWS_ACCESS_KEY_ID=votre_clé_aws
AWS_SECRET_ACCESS_KEY=votre_clé_secrète_aws
AWS_STORAGE_BUCKET_NAME=votre_bucket
```

### **Dépendances Backend**
```
Django==4.2.7
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0
django-cors-headers==4.3.1
psycopg2-binary==2.9.7
python-decouple==3.8
```

### **Dépendances Frontend**
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "axios": "^1.6.0",
  "react-router-dom": "^6.8.0",
  "tailwindcss": "^3.3.0",
  "recordrtc": "^5.6.2"
}
```

## 📊 Métriques et Monitoring

### **Métriques Clés**
- Taux de completion des entretiens
- Temps moyen par question
- Taux d'erreur technique
- Satisfaction utilisateur

### **Logs Techniques**
- Sessions démarrées/terminées
- Erreurs d'enregistrement
- Problèmes de réseau
- Performance du serveur

## 🎯 Prochaines Étapes

1. **Démarrer le serveur Django** : `python manage.py runserver`
2. **Tester l'API** avec Postman ou curl
3. **Développer l'interface React** pour les recruteurs
4. **Implémenter l'enregistrement vidéo** côté candidat
5. **Ajouter les tests automatisés**
6. **Déployer en production** avec monitoring

---

*Documentation mise à jour le : $(date)*
