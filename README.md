# 🔍 Domain Monitor - SaaS Monitoring Domaines Expirés

Application de surveillance automatique de domaines expirés avec notifications Discord en temps réel.

## 🚀 Fonctionnalités

- ✅ Surveillance automatique de domaines expirés (toutes les 2 heures)
- ✅ Double vérification DNS pour éviter les faux positifs
- ✅ Notifications Discord lors de la disponibilité
- ✅ API REST complète pour la gestion des domaines
- ✅ Support des extensions .fr, .com, .net
- ✅ Interface phpMyAdmin pour administrer la base de données MySQL
- ✅ Logs structurés avec rotation automatique
- ✅ Architecture async pour performance optimale

## 🛠️ Stack Technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Runtime | Python | 3.12 |
| Framework API | FastAPI | ≥0.109 |
| Base de données | MySQL | 8.0 |
| Admin BDD | phpMyAdmin | latest |
| ORM | SQLAlchemy | ≥2.0 |
| Scheduler | APScheduler | ≥3.10 |
| DNS | dnspython | ≥2.5 |
| Logs | Loguru | ≥0.7 |
| Conteneurisation | Docker | latest |

## 📦 Installation

### Prérequis

- Docker et Docker Compose installés
- Un webhook Discord ([créer un webhook](https://support.discord.com/hc/fr/articles/228383668))
- Git

### Déploiement Local

1. **Cloner le repository**
```bash
git clone https://github.com/mehdilb8/saas-nomdedomaine.git
cd saas-nomdedomaine
```

2. **Configurer l'environnement**
```bash
cp .env.example .env
nano .env  # Modifier les variables
```

Variables importantes à configurer dans `.env` :
```bash
# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# MySQL (modifier les mots de passe)
MYSQL_PASSWORD=votre_mot_de_passe_securise
MYSQL_ROOT_PASSWORD=votre_mot_de_passe_root_securise
```

3. **Démarrer l'application**
```bash
docker compose up -d --build
```

4. **Vérifier le statut**
```bash
docker compose ps
docker compose logs -f app
```

## 🌐 Accès aux Services

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:3010 | API REST FastAPI |
| Documentation API | http://localhost:3010/docs | Swagger UI interactif |
| phpMyAdmin | http://localhost:8083 | Administration MySQL |
| Logs | `./logs/app.log` | Fichiers de logs |

### Connexion phpMyAdmin

- **URL** : http://localhost:8083
- **Serveur** : `mysql`
- **Utilisateur** : `root`
- **Mot de passe** : Valeur de `MYSQL_ROOT_PASSWORD` dans `.env`

## 🔌 API Endpoints

### Santé et Statistiques

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/health` | Health check (Docker) |
| GET | `/api/stats` | Statistiques globales |

### Gestion des Domaines

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/domains` | Lister les domaines (avec filtres) |
| GET | `/api/domains/{id}` | Détails d'un domaine |
| POST | `/api/domains` | Ajouter un domaine |
| PUT | `/api/domains/{id}` | Modifier un domaine |
| DELETE | `/api/domains/{id}` | Supprimer un domaine |
| POST | `/api/domains/{id}/check` | Forcer vérification |
| PATCH | `/api/domains/{id}/toggle` | Activer/désactiver monitoring |

## 📝 Exemples d'Utilisation

### Ajouter un Domaine

```bash
curl -X POST http://localhost:3010/api/domains \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.fr",
    "niche": "Tech",
    "traffic": 5000,
    "referring_domains": 150
  }'
```

### Lister les Domaines

```bash
# Tous les domaines
curl http://localhost:3010/api/domains

# Filtrer par TLD
curl http://localhost:3010/api/domains?tld=fr

# Filtrer par statut
curl http://localhost:3010/api/domains?status=available

# Recherche
curl http://localhost:3010/api/domains?search=example
```

### Forcer une Vérification

```bash
curl -X POST http://localhost:3010/api/domains/1/check
```

### Obtenir les Statistiques

```bash
curl http://localhost:3010/api/stats
```

## 📁 Structure du Projet

```
saas-nomdedomaine/
├── app/
│   ├── main.py              # Application FastAPI
│   ├── config.py            # Configuration
│   ├── database.py          # Connexion MySQL
│   ├── models.py            # Modèles SQLAlchemy
│   ├── schemas.py           # Schémas Pydantic
│   ├── services/
│   │   ├── dns_checker.py   # Vérification DNS
│   │   ├── availability.py  # Orchestration vérification
│   │   ├── notification.py  # Notifications Discord
│   │   └── scheduler.py     # Scheduler APScheduler
│   └── routers/
│       └── domains.py       # Routes API
├── tests/                   # Tests unitaires
├── scripts/
│   ├── init.sql            # Initialisation MySQL
│   └── seed.py             # Données de test
├── docker/
│   └── Dockerfile          # Image Docker
├── docker-compose.yml      # Configuration Docker
├── requirements.txt        # Dépendances Python
└── .env                    # Configuration (gitignored)
```

## 🧪 Tests

Exécuter les tests :

```bash
# Installer les dépendances de test
pip install -r requirements.txt

# Lancer les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html
```

## 🔧 Configuration Avancée

### Modifier l'Intervalle de Vérification

Dans `.env` :
```bash
CHECK_INTERVAL_HOURS=2  # Vérifier toutes les 2 heures
```

### Ajouter des TLDs Supportés

Dans `.env` :
```bash
SUPPORTED_TLDS=fr,com,net,org,io
```

### Configurer les Serveurs DNS

Dans `.env` :
```bash
DNS_PRIMARY_SERVER=8.8.8.8      # Google DNS
DNS_SECONDARY_SERVER=1.1.1.1    # Cloudflare DNS
```

## 📊 Base de Données

### Tables Principales

- **domains** : Liste des domaines surveillés
- **check_logs** : Historique des vérifications
- **notifications** : Historique des notifications Discord

### Accès Direct MySQL

```bash
docker compose exec mysql mysql -u root -p domain_monitor
```

Requêtes utiles :
```sql
-- Voir tous les domaines
SELECT * FROM domains;

-- Domaines disponibles
SELECT * FROM domains WHERE status = 'available';

-- Dernières vérifications
SELECT * FROM check_logs ORDER BY checked_at DESC LIMIT 20;
```

## 🐛 Dépannage

### Les containers ne démarrent pas

```bash
# Vérifier les logs
docker compose logs

# Redémarrer proprement
docker compose down
docker compose up -d --build
```

### MySQL ne démarre pas

```bash
# Vérifier les logs MySQL
docker compose logs mysql

# Supprimer le volume et recréer
docker compose down -v
docker compose up -d
```

### L'application ne se connecte pas à MySQL

Vérifier que `MYSQL_HOST=mysql` dans `.env` (nom du service Docker).

### Les notifications Discord ne fonctionnent pas

1. Vérifier que `DISCORD_WEBHOOK_URL` est correct dans `.env`
2. Tester le webhook :
```bash
curl -X POST http://localhost:3010/api/test-notification
```

## 📄 License

MIT

## 👤 Auteur

Mehdi LB - [GitHub](https://github.com/mehdilb8)

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📚 Documentation Complète

Pour plus de détails sur le déploiement en production, consultez [DEPLOYMENT.md](DEPLOYMENT.md).
