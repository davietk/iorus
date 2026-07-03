# LED Matrix Dashboard (Raspberry Pi + Home Assistant)

Projet Python pour afficher des informations dynamiques sur une matrice LED 64x32:
- Meteo (Open-Meteo)
- Bourse (Finnhub)
- Actualites (NewsAPI)
- Entites Home Assistant (API REST)
- Publication des etats vers Home Assistant via MQTT (auto-discovery)

## 1) Prerequis materiels

- Raspberry Pi (3, 4 ou 5 recommande)
- Matrice LED HUB75 64x32
- HAT/adaptateur compatible `rpi-rgb-led-matrix`
- Alimentation adaptee a la matrice

## 2) Installation logicielle (Raspberry Pi OS)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git build-essential cmake
```

Clone du projet puis installation:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Driver matrice LED

Le rendu materiel repose sur `rpi-rgb-led-matrix` (bibliotheque C++/Python).
Installe-la sur le Pi selon la documentation officielle:
https://github.com/hzeller/rpi-rgb-led-matrix

Si la bibliotheque n'est pas disponible, l'application tourne en mode console (simulation texte).

Si tu vois une erreur de type `Need root ... run as root or with --led-no-hardware-pulse`:
- active `display.no_hardware_pulse: true` dans `config.yaml` pour lancer sans root
- ou lance l'application en root (`sudo`) pour garder le mode hardware pulse

## 3) Configuration

Copie la config d'exemple:

```bash
cp config.example.yaml config.yaml
```

Variables d'environnement (si connecteurs actives):

```bash
export FINNHUB_API_TOKEN="..."
export NEWSAPI_KEY="..."
export HA_TOKEN="..."
```

Puis adapte `config.yaml`:
- Coordonnees meteo
- Symboles boursiers
- Requete actualites
- Entites Home Assistant a afficher
- Parametres MQTT de Home Assistant

## 4) Lancement

```bash
source .venv/bin/activate
python -m app.main --config config.yaml
```

## 5) Home Assistant

L'app publie automatiquement des entites `sensor` via MQTT discovery:
- Statut global du dashboard
- Un sensor par connecteur actif

Dans Home Assistant:
1. Active MQTT
2. Verifie que le broker est joignable depuis le Raspberry Pi
3. Lance l'application
4. Les entites apparaissent automatiquement

## 6) Connecteurs disponibles

- `weather_openmeteo`: meteo actuelle sans cle API
- `stocks_finnhub`: cours boursiers (requiert `FINNHUB_API_TOKEN`)
- `news_newsapi`: headlines actualites (requiert `NEWSAPI_KEY`)
- `homeassistant_entities`: lecture directe des entites HA (requiert `HA_TOKEN`)

## 7) Ajouter un nouveau connecteur

1. Cree un fichier dans `app/connectors/`
2. Herite de `BaseConnector`
3. Retourne une liste de `ConnectorItem`
4. Enregistre le type dans le registre `CONNECTOR_FACTORIES`

## 8) Deploiement automatique Raspberry Pi (systemd)

Fichiers inclus:
- `deploy/led-matrix-dashboard.service`
- `scripts/install_pi.sh`

Sur le Raspberry Pi:

```bash
sudo bash scripts/install_pi.sh
```

Le script:
- Installe les dependances systeme
- Copie le projet vers `/opt/led-matrix-dashboard`
- Cree la venv et installe les paquets Python
- Cree `config.yaml` si absent
- Cree `/etc/default/led-matrix-dashboard` pour les tokens
- Installe/active le service `led-matrix-dashboard`

Commandes de supervision:

```bash
sudo systemctl status led-matrix-dashboard
sudo journalctl -u led-matrix-dashboard -f
```
