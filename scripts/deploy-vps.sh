#!/bin/bash

# ============================================
# SCRIPT DE DÉPLOIEMENT VPS - DOMAIN MONITOR
# ============================================

set -e  # Arrêter en cas d'erreur

echo "============================================"
echo "🚀 DÉPLOIEMENT DOMAIN MONITOR SUR VPS"
echo "============================================"

# Variables
REPO_URL="https://github.com/mehdilb8/saas-nomdedomaine.git"
APP_DIR="$HOME/saas-nomdedomaine"
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1462878358655205427/JP1kSyQmWYTg-h2FDXjeVFLfWori5Mq6b5IR4Ufsn5WJM6gZompa9VvlQUScWNbwwssl"

# ============================================
# 1. VÉRIFIER DOCKER
# ============================================
echo ""
echo "📦 Vérification de Docker..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Installation..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installé. Veuillez vous reconnecter et relancer ce script."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Installation..."
    sudo apt update
    sudo apt install -y docker-compose-plugin
fi

echo "✅ Docker et Docker Compose sont installés"

# ============================================
# 2. CLONER OU METTRE À JOUR LE REPOSITORY
# ============================================
echo ""
echo "📥 Récupération du code..."

if [ -d "$APP_DIR" ]; then
    echo "📂 Le dossier existe déjà, mise à jour..."
    cd "$APP_DIR"
    git pull origin master
else
    echo "📂 Clonage du repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "✅ Code récupéré"

# ============================================
# 3. CONFIGURER .ENV
# ============================================
echo ""
echo "⚙️ Configuration de l'environnement..."

if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env..."
    cp .env.example .env

    # Générer des mots de passe sécurisés
    MYSQL_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    # Remplacer les valeurs dans .env
    sed -i "s|MYSQL_PASSWORD=.*|MYSQL_PASSWORD=$MYSQL_PASSWORD|g" .env
    sed -i "s|MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD|g" .env
    sed -i "s|DISCORD_WEBHOOK_URL=.*|DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK|g" .env

    echo "✅ Fichier .env créé avec mots de passe sécurisés"
    echo ""
    echo "🔐 MOTS DE PASSE GÉNÉRÉS (SAUVEGARDEZ-LES) :"
    echo "   MySQL User Password: $MYSQL_PASSWORD"
    echo "   MySQL Root Password: $MYSQL_ROOT_PASSWORD"
    echo ""
else
    echo "✅ Fichier .env existe déjà"
fi

# ============================================
# 4. CRÉER LES DOSSIERS NÉCESSAIRES
# ============================================
echo ""
echo "📁 Création des dossiers..."

mkdir -p logs mysql_data

echo "✅ Dossiers créés"

# ============================================
# 5. ARRÊTER LES ANCIENS CONTAINERS (si existants)
# ============================================
echo ""
echo "🛑 Arrêt des anciens containers..."

docker compose down 2>/dev/null || true

echo "✅ Anciens containers arrêtés"

# ============================================
# 6. BUILD ET DÉMARRAGE
# ============================================
echo ""
echo "🏗️ Build de l'application..."

docker compose build --no-cache

echo ""
echo "🚀 Démarrage des services..."

docker compose up -d

echo "✅ Services démarrés"

# ============================================
# 7. ATTENDRE QUE LES SERVICES SOIENT PRÊTS
# ============================================
echo ""
echo "⏳ Attente du démarrage des services (30 secondes)..."

sleep 30

# ============================================
# 8. VÉRIFIER LE STATUT
# ============================================
echo ""
echo "🔍 Vérification du statut..."

docker compose ps

echo ""
echo "📊 Logs de l'application (dernières 20 lignes):"
docker compose logs --tail=20 app

# ============================================
# 9. TEST DE L'API
# ============================================
echo ""
echo "🧪 Test de l'API..."

if curl -f http://localhost:3010/api/health &> /dev/null; then
    echo "✅ API répond correctement"
else
    echo "⚠️ L'API ne répond pas encore, vérifiez les logs"
fi

# ============================================
# 10. AFFICHER LES INFORMATIONS D'ACCÈS
# ============================================
echo ""
echo "============================================"
echo "✅ DÉPLOIEMENT TERMINÉ !"
echo "============================================"
echo ""
echo "📍 ACCÈS AUX SERVICES :"
echo ""
echo "   🌐 API FastAPI"
echo "      URL: http://$(curl -s ifconfig.me):3010"
echo "      Health: http://$(curl -s ifconfig.me):3010/api/health"
echo "      Docs: http://$(curl -s ifconfig.me):3010/docs"
echo ""
echo "   🗄️ phpMyAdmin"
echo "      URL: http://$(curl -s ifconfig.me):8083"
echo "      User: root"
echo "      Password: (voir ci-dessus)"
echo ""
echo "   📊 Statistiques"
echo "      URL: http://$(curl -s ifconfig.me):3010/api/stats"
echo ""
echo "============================================"
echo "📝 COMMANDES UTILES :"
echo "============================================"
echo ""
echo "   Voir les logs:"
echo "   docker compose logs -f"
echo ""
echo "   Redémarrer:"
echo "   docker compose restart"
echo ""
echo "   Arrêter:"
echo "   docker compose down"
echo ""
echo "   Mettre à jour:"
echo "   git pull && docker compose up -d --build"
echo ""
echo "============================================"
