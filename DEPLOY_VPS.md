# 🚀 Guide de Déploiement VPS - Domain Monitor

Guide complet pour déployer l'application sur votre VPS OVH.

## 📋 Informations VPS

- **IP** : 37.59.125.246 (à confirmer)
- **OS** : Ubuntu 22.04+
- **Ressources** : 8 vCores, 24 Go RAM, 200 Go SSD NVMe
- **Ports utilisés** : 3010 (API), 8083 (phpMyAdmin), 3307 (MySQL interne)

---

## 🚀 Déploiement Automatique (Recommandé)

### Étape 1 : Connexion au VPS

```bash
ssh ubuntu@37.59.125.246
# ou
ssh root@37.59.125.246
```

### Étape 2 : Télécharger et exécuter le script de déploiement

```bash
# Télécharger le script
curl -o deploy.sh https://raw.githubusercontent.com/mehdilb8/saas-nomdedomaine/master/scripts/deploy-vps.sh

# Rendre exécutable
chmod +x deploy.sh

# Exécuter
./deploy.sh
```

Le script va automatiquement :
- ✅ Installer Docker et Docker Compose (si nécessaire)
- ✅ Cloner le repository GitHub
- ✅ Créer le fichier .env avec mots de passe sécurisés
- ✅ Build l'application
- ✅ Démarrer tous les services (app, MySQL, phpMyAdmin)
- ✅ Afficher les URLs d'accès

**⏱️ Durée estimée : 5-10 minutes**

---

## 🔧 Déploiement Manuel (Alternative)

### 1. Installer Docker

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

**⚠️ Important : Déconnectez-vous et reconnectez-vous après l'installation de Docker**

### 2. Cloner le Repository

```bash
cd ~
git clone https://github.com/mehdilb8/saas-nomdedomaine.git
cd saas-nomdedomaine
```

### 3. Configurer l'Environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer le fichier .env
nano .env
```

**Variables à modifier obligatoirement :**

```bash
# Changer les mots de passe MySQL
MYSQL_PASSWORD=VotreMotDePasseSecurise123!
MYSQL_ROOT_PASSWORD=VotreMotDePasseRootSecurise456!

# Le webhook Discord est déjà configuré dans .env.example
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1462878358655205427/JP1kSyQmWYTg-h2FDXjeVFLfWori5Mq6b5IR4Ufsn5WJM6gZompa9VvlQUScWNbwwssl
```

Sauvegarder : `Ctrl+O`, `Enter`, `Ctrl+X`

### 4. Créer les Dossiers

```bash
mkdir -p logs mysql_data
```

### 5. Démarrer l'Application

```bash
# Build et démarrage
docker compose up -d --build

# Vérifier les logs
docker compose logs -f
```

---

## 🌐 Accès aux Services

Une fois déployé, les services sont accessibles :

### API FastAPI
- **URL** : http://VOTRE_IP_VPS:3010
- **Health Check** : http://VOTRE_IP_VPS:3010/api/health
- **Documentation** : http://VOTRE_IP_VPS:3010/docs
- **Stats** : http://VOTRE_IP_VPS:3010/api/stats

### phpMyAdmin
- **URL** : http://VOTRE_IP_VPS:8083
- **Serveur** : `mysql`
- **Utilisateur** : `root`
- **Mot de passe** : Celui défini dans `.env` (MYSQL_ROOT_PASSWORD)

### Logs
- **Fichiers** : `~/saas-nomdedomaine/logs/app.log`
- **Docker** : `docker compose logs -f app`

---

## 🔍 Vérification du Déploiement

### 1. Vérifier que les containers tournent

```bash
docker compose ps
```

Vous devriez voir 3 services en état "running" :
- `domain-monitor-app`
- `domain-monitor-mysql`
- `domain-monitor-phpmyadmin`

### 2. Tester l'API

```bash
# Health check
curl http://localhost:3010/api/health

# Statistiques
curl http://localhost:3010/api/stats
```

### 3. Vérifier les logs

```bash
# Logs de l'application
docker compose logs app

# Logs en temps réel
docker compose logs -f app
```

### 4. Accéder à phpMyAdmin

Ouvrez dans votre navigateur : `http://VOTRE_IP_VPS:8083`

---

## 🧪 Tester l'Application

### Ajouter un domaine de test

```bash
curl -X POST http://localhost:3010/api/domains \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test-domain-xyz.fr",
    "niche": "Test",
    "traffic": 1000,
    "referring_domains": 50
  }'
```

**Ce qui va se passer :**
1. ✅ Vérification immédiate avec DNS AFNIC
2. ✅ Si disponible → Notification Discord + Watcher démarre (check toutes les 2s)
3. ✅ Si indisponible → Statut mis à jour

### Voir les domaines

```bash
curl http://localhost:3010/api/domains
```

### Voir les watchers actifs

```bash
curl http://localhost:3010/api/stats | grep active_watchers
```

---

## 🔧 Commandes de Gestion

### Voir les logs

```bash
# Tous les services
docker compose logs -f

# Application uniquement
docker compose logs -f app

# MySQL uniquement
docker compose logs -f mysql

# Dernières 100 lignes
docker compose logs --tail=100 app
```

### Redémarrer les services

```bash
# Tous les services
docker compose restart

# Application uniquement
docker compose restart app
```

### Arrêter les services

```bash
docker compose down
```

### Mettre à jour l'application

```bash
cd ~/saas-nomdedomaine
git pull origin master
docker compose up -d --build
```

### Voir l'utilisation des ressources

```bash
docker stats
```

---

## 🗄️ Gestion de la Base de Données

### Accès MySQL en ligne de commande

```bash
docker compose exec mysql mysql -u root -p domain_monitor
```

### Backup de la base de données

```bash
# Créer un backup
docker compose exec mysql mysqldump -u root -p domain_monitor > backup_$(date +%Y%m%d_%H%M%S).sql

# Avec compression
docker compose exec mysql mysqldump -u root -p domain_monitor | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restaurer un backup

```bash
docker compose exec -T mysql mysql -u root -p domain_monitor < backup_20250119_120000.sql
```

### Requêtes SQL utiles

```sql
-- Voir tous les domaines
SELECT * FROM domains;

-- Domaines disponibles avec watcher actif
SELECT * FROM domains WHERE status = 'available' AND is_active = TRUE;

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

---

## 🔐 Sécurité

### Configurer le Firewall (UFW)

```bash
# Activer UFW
sudo ufw enable

# Autoriser SSH
sudo ufw allow 22/tcp

# Autoriser l'API
sudo ufw allow 3010/tcp

# Autoriser phpMyAdmin (optionnel)
sudo ufw allow 8083/tcp

# Vérifier
sudo ufw status
```

### Sécuriser phpMyAdmin

**Option 1 : Accès via tunnel SSH (Recommandé)**

Sur votre machine locale :
```bash
ssh -L 8083:localhost:8083 ubuntu@VOTRE_IP_VPS
```

Puis accéder à : `http://localhost:8083`

**Option 2 : Désactiver phpMyAdmin en production**

Commentez le service dans `docker-compose.yml` :
```yaml
#  phpmyadmin:
#    image: phpmyadmin:latest
#    ...
```

Puis : `docker compose up -d`

---

## 📊 Monitoring

### Voir les watchers actifs

```bash
curl http://localhost:3010/api/stats | jq '.active_watchers'
```

### Voir les domaines surveillés

```bash
curl http://localhost:3010/api/domains?status=available
```

### Logs en temps réel

```bash
# Application
tail -f ~/saas-nomdedomaine/logs/app.log

# Erreurs uniquement
tail -f ~/saas-nomdedomaine/logs/error.log
```

---

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
# Vérifier les logs
docker compose logs mysql

# Vérifier l'espace disque
df -h

# Supprimer les données et recréer (⚠️ PERTE DE DONNÉES)
docker compose down -v
docker compose up -d
```

### L'API ne répond pas

```bash
# Vérifier que le container tourne
docker compose ps

# Vérifier les logs
docker compose logs app

# Tester la connexion
curl http://localhost:3010/api/health
```

### Les notifications Discord ne fonctionnent pas

```bash
# Vérifier le webhook dans .env
grep DISCORD_WEBHOOK_URL .env

# Tester manuellement
curl -X POST http://localhost:3010/api/domains/1/check

# Vérifier les logs
docker compose logs app | grep Discord
```

---

## 🔄 Backup Automatique

Créer un script de backup automatique :

```bash
nano ~/backup-domain-monitor.sh
```

Contenu :
```bash
#!/bin/bash
BACKUP_DIR=~/backups/domain-monitor
mkdir -p $BACKUP_DIR
cd ~/saas-nomdedomaine

# Backup MySQL
docker compose exec -T mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} domain_monitor | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Garder seulement les 7 derniers backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $(date)"
```

Rendre exécutable et ajouter au cron :
```bash
chmod +x ~/backup-domain-monitor.sh

# Backup quotidien à 3h du matin
crontab -e
# Ajouter :
0 3 * * * ~/backup-domain-monitor.sh >> ~/backup-domain-monitor.log 2>&1
```

---

## 📞 Support

En cas de problème :
1. Vérifier les logs : `docker compose logs -f`
2. Consulter la documentation : [README.md](../README.md)
3. Ouvrir une issue sur GitHub

---

## ✅ Checklist de Déploiement

- [ ] Docker et Docker Compose installés
- [ ] Repository cloné
- [ ] Fichier .env configuré avec mots de passe sécurisés
- [ ] Webhook Discord configuré
- [ ] Services démarrés (`docker compose up -d`)
- [ ] API accessible (http://IP:3010/api/health)
- [ ] phpMyAdmin accessible (http://IP:8083)
- [ ] Firewall configuré
- [ ] Backup automatique configuré
- [ ] Test d'ajout de domaine effectué
- [ ] Notification Discord reçue

---

**Déploiement terminé ! Votre application Domain Monitor est maintenant en production ! 🎉**
