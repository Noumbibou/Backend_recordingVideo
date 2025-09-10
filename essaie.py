import requests

# URL de ton endpoint login
url = "http://127.0.0.1:8000/auth/login/"

# Données du login (email et mot de passe)
data = {
    "email": "fotso@gmail.com",  # remplace par ton email
    "password": "alex0204"           # remplace par ton mot de passe
}

# Headers pour indiquer que l'on envoie du JSON
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

try:
    response = requests.post(url, json=data, headers=headers)
    
    print("Status Code:", response.status_code)
    
    # Si réponse JSON
    try:
        print("Response JSON:", response.json())
    except ValueError:
        print("Response Text:", response.text)

except requests.exceptions.RequestException as e:
    print("Erreur de connexion :", e)
