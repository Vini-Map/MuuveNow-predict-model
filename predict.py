import os
import joblib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

ORS_API_KEY = "5b3ce3597851110001cf624855631f968bc045de9321e2911cf0396f"
ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

# Carrega os modelos
modelos = {}
modelos_path = os.path.join(os.getcwd(), "modelos")
for nome_arquivo in os.listdir(modelos_path):
    if nome_arquivo.endswith(".pkl"):
        categoria = nome_arquivo.replace("model_", "").replace(".pkl", "")
        modelos[categoria] = joblib.load(os.path.join(modelos_path, nome_arquivo))

def geocode(endereco):
    params = {
        "api_key": ORS_API_KEY,
        "text": endereco,
        "size": 1
    }
    response = requests.get(ORS_GEOCODE_URL, params=params)
    if response.status_code == 200:
        features = response.json().get("features")
        if features:
            coords = features[0]["geometry"]["coordinates"]
            return coords[1], coords[0]
    return None, None

def calcular_rota(lat1, lon1, lat2, lon2):
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body = {"coordinates": [[lon1, lat1], [lon2, lat2]]}
    response = requests.post(ORS_DIRECTIONS_URL, json=body, headers=headers)
    if response.status_code == 200:
        segmento = response.json()["features"][0]["properties"]["segments"][0]
        distancia_km = segmento["distance"] / 1000
        duracao_min = segmento["duration"] / 60
        return round(distancia_km, 2), round(duracao_min, 2)
    return None, None

@app.route("/", methods=["POST"])
def prever():
    data = request.json
    origem = data.get("origem")
    destino = data.get("destino")
    if not origem or not destino:
        return jsonify({"erro": "Campos obrigatórios: origem, destino"}), 400

    lat1, lon1 = geocode(origem)
    lat2, lon2 = geocode(destino)

    if None in [lat1, lon1, lat2, lon2]:
        return jsonify({"erro": "Erro ao geocodificar os endereços"}), 400

    distancia, duracao = calcular_rota(lat1, lon1, lat2, lon2)
    if distancia is None:
        return jsonify({"erro": "Erro ao calcular rota"}), 500

    precos = {
        categoria: round(model.predict([[distancia, duracao]])[0], 2)
        for categoria, model in modelos.items()
    }

    return jsonify({
        "origem": origem,
        "destino": destino,
        "distancia_km": distancia,
        "duracao_min": duracao,
        "precos_estimados": precos
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
