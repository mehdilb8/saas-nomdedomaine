# 🚀 Guide de Déploiement - Domain Monitor

Guide complet pour déployer et gérer l'application Domain Monitor sur un serveur VPS.

## 📋 Prérequis Serveur

- Ubuntu 22.04+ (ou autre distribution Linux)
- Docker et Docker Compose installés
- Accès SSH au serveur
- Ports disponibles : 3010 (API), 8083 (phpMyAdmin), 3307 (MySQL)

## 🔧 Installation Docker (si nécessaire)

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo apt install docker-compose-plugin -y

# Vérifier l'installation
docker --version
docker compose version
```

## 📦 Déploiement sur VPS

### 1. Connexion au Serveur

```bash
ssh ubuntu@VOTRE_IP_VPS
```

### 2. Cloner le Repository

```bash
cd ~
git clone https://github.com/mehdilb8/saas-nomdedomaine.git
cd saas-nomdedomaine
```

### 3. Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer la configuration
nano .env
```

**Variables importantes à configurer :**

```bash
# Application
APP_ENV=production
APP_DEBUG=false

# MySQL - CHANGER LES MOTS DE PASSE !
MYSQL_PASSWORD=VotreMotDePasseSecurise123!
MYSQL_ROOT_PASSWORD=VotreMotDePasseRootSecurise456!

# Discord - Votre webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN

# Scheduler
CHECK_INTERVAL_HOURS=2
```

### 4. Démarrer l'Application

```bash
# Build et démarrage
docker compose up -d --build

# Vérifier les logs
docker compose logs -f
```

### 5. Vérifier le Déploiement

```bash
# Vérifier que les containers tournent
docker compose ps

# Tester l'API
curl http://localhost:3010/api/health

# Vérifier les logs
docker compose logs app
```

## 🌐 Services et Ports

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| API FastAPI | 3010 | http://IP_VPS:3010 | API REST |
| phpMyAdmin | 8083 | http://IP_VPS:8083 | Admin MySQL |
| MySQL | 3307 | localhost:3307 | Base de données (interne) |

**Note :** MySQL n'est pas exposé publiquement pour des raisons de sécurité.

## 🔐 Sécurité

### Firewall (UFW)

```bash
# Activer le firewall
sudo ufw enable

# Autoriser SSH
sudo ufw allow 22/tcp

# Autoriser l'API
sudo ufw allow 3010/tcp

# Autoriser phpMyAdmin (optionnel, à sécuriser)
sudo ufw allow 8083/tcp

# Vérifier le statut
sudo ufw status
```

### Sécuriser phpMyAdmin

Pour sécuriser phpMyAdmin en production :

1. **Option 1 : Accès via tunnel SSH**
```bash
# Sur votre machine locale
ssh -L 8083:localhost:8083 ubuntu@VOTRE_IP_VPS

# Puis accéder à http://localhost:8083
```

2. **Option 2 : Désactiver phpMyAdmin**
```bash
# Modifier docker-compose.yml pour commenter le service phpmyadmin
docker compose up -d
```

## 📊 Commandes de Gestion

### Gestion des Containers

```bash
# Voir l'état
docker compose ps

# Voir les logs en temps réel
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f app
docker compose logs -f mysql

# Redémarrer tous les services
docker compose restart

# Redémarrer un service spécifique
docker compose restart app

# Arrêter tous les services
docker compose down

# Démarrer tous les services
docker compose up -d
```

### Mise à Jour de l'Application

```bash
# Récupérer les dernières modifications
git pull origin master

# Rebuild et redémarrage
docker compose up -d --build

# Vérifier les logs
docker compose logs -f app
```

### Gestion de la Base de Données

#### Accès MySQL en ligne de commande

```bash
docker compose exec mysql mysql -u root -p domain_monitor
```

#### Backup de la Base de Données

```bash
# Créer un backup
docker compose exec mysql mysqldump -u root -p domain_monitor > backup_$(date +%Y%m%d_%H%M%S).sql

# Avec compression
docker compose exec mysql mysqldump -u root -p domain_monitor | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### Restaurer un Backup

```bash
# Restaurer depuis un backup
docker compose exec -T mysql mysql -u root -p domain_monitor < backup_20250119_120000.sql

# Depuis un backup compressé
gunzip < backup_20250119_120000.sql.gz | docker compose exec -T mysql mysql -u root -p domain_monitor
```

#### Requêtes SQL Utiles

```sql
-- Voir tous les domaines
SELECT * FROM domains;

-- Domaines disponibles
SELECT * FROM domains WHERE status = 'available';

-- Domaines actifs
SELECT * FROM domains WHERE is_active = TRUE;

-- Statistiques par TLD
SELECT tld, COUNT(*) as count FROM domains GROUP BY tld;

-- Dernières vérifications
SELECT d.domain, cl.status_found, cl.checked_at
FROM check_logs cl
JOIN domains d ON cl.domain_id = d.id
ORDER BY cl.checked_at DESC
LIMIT 20;

-- Notifications envoyées aujourd'hui
SELECT COUNT(*) FROM notifications
WHERE DATE(sent_at) = CURDATE() AND success = TRUE;
```

## 🔍 Monitoring et Logs

### Voir les Logs

```bash
# Logs de l'application
tail -f logs/app.log

# Logs d'erreurs uniquement
tail -f logs/error.log

# Logs Docker
docker compose logs --tail=100 app
```

### Vérifier la Santé de l'Application

```bash
# Health check
curl http://localhost:3010/api/health

# Statistiques
curl http://localhost:3010/api/stats
```

## 🔄 Automatisation

### Backup Automatique (Cron)

Créer un script de backup automatique :

```bash
# Créer le script
nano ~/backup-domain-monitor.sh
```

Contenu du script :
```bash
#!/bin/bash
BACKUP_DIR=~/backups/domain-monitor
mkdir -p $BACKUP_DIR
cd ~/saas-nomdedomaine
docker compose exec -T mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} domain_monitor | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Garder seulement les 7 derniers backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

Rendre exécutable et ajouter au cron :
```bash
chmod +x ~/backup-domain-monitor.sh

# Ajouter au crontab (backup quotidien à 3h du matin)
crontab -e
# Ajouter cette ligne :
0 3 * * * ~/backup-domain-monitor.sh
```

### Redémarrage Automatique

Docker Compose est configuré avec `restart: unless-stopped`, donc les containers redémarrent automatiquement après un reboot du serveur.

## 🐛 Dépannage

### L'application ne démarre pas

```bash
# Vérifier les logs
docker compose logs app

# Vérifier la configuration
cat .env

# Redémarrage complet
docker compose down
docker compose up -d --build
```

### MySQL ne démarre pas

```bash
# Vérifier les logs MySQL
docker compose logs mysql

# Vérifier l'espace disque
df -h

# En dernier recours (ATTENTION : supprime les données)
docker compose down -v
docker compose up -d
```

### Erreur de connexion à la base de données

1. Vérifier que MySQL est démarré : `docker compose ps`
2. Vérifier les credentials dans `.env`
3. Vérifier que `MYSQL_HOST=mysql` (nom du service Docker)

### Les notifications Discord ne fonctionnent pas

1. Vérifier le webhook dans `.env`
2. Tester manuellement :
```bash
curl -X POST "http://localhost:3010/api/domains/1/check"
```
3. Vérifier les logs : `docker compose logs app | grep Discord`

### Problème de permissions

```bash
# Donner les bonnes permissions aux logs
sudo chown -R $USER:$USER logs/

# Recréer les containers
docker compose down
docker compose up -d
```

## 📈 Optimisation

### Augmenter les Performances

Dans `.env` :
```bash
# Augmenter la taille des batches
BATCH_SIZE=100

# Réduire le délai entre les checks
DELAY_BETWEEN_CHECKS_MS=50
```

### Limiter l'Utilisation des Ressources

Modifier `docker-compose.yml` pour ajouter des limites :
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## 📞 Support

En cas de problème :
1. Vérifier les logs : `docker compose logs -f`
2. Consulter la documentation : [README.md](README.md)
3. Ouvrir une issue sur GitHub

## 🔄 Mise à Jour de Version

```bash
# Sauvegarder la base de données
docker compose exec mysql mysqldump -u root -p domain_monitor > backup_before_update.sql

# Récupérer les mises à jour
git pull origin master

# Rebuild
docker compose up -d --build

# Vérifier
docker compose logs -f app
```

---

**Dernière mise à jour :** 2025-01-19
