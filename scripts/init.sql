-- ============================================
-- DOMAIN MONITOR - INITIALISATION BASE DE DONNÉES
-- ============================================

-- Création de la base de données (si pas déjà créée par Docker)
CREATE DATABASE IF NOT EXISTS domain_monitor
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE domain_monitor;

-- ============================================
-- TABLE: domains
-- ============================================
CREATE TABLE IF NOT EXISTS domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE COMMENT 'Nom de domaine complet (ex: example.fr)',
    tld VARCHAR(10) NOT NULL COMMENT 'Extension du domaine (.fr, .com, .net)',
    niche VARCHAR(100) NULL COMMENT 'Thématique du domaine',
    traffic INT DEFAULT 0 COMMENT 'Estimation du trafic mensuel',
    referring_domains INT DEFAULT 0 COMMENT 'Nombre de referring domains (backlinks)',
    status ENUM('available', 'unavailable', 'unknown') DEFAULT 'unknown' COMMENT 'Statut actuel',
    previous_status ENUM('available', 'unavailable', 'unknown') DEFAULT 'unknown' COMMENT 'Statut précédent (pour détecter les transitions)',
    last_checked DATETIME NULL COMMENT 'Date de dernière vérification',
    last_available DATETIME NULL COMMENT 'Date de dernière disponibilité détectée',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Monitoring actif/inactif',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_is_active (is_active),
    INDEX idx_status (status),
    INDEX idx_tld (tld),
    INDEX idx_last_checked (last_checked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABLE: check_logs
-- ============================================
CREATE TABLE IF NOT EXISTS check_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_id INT NOT NULL,
    status_found ENUM('available', 'unavailable', 'error') NOT NULL COMMENT 'Résultat de la vérification',
    check_method VARCHAR(20) NOT NULL COMMENT 'Méthode utilisée (dns_primary, dns_secondary)',
    response_time_ms INT NULL COMMENT 'Temps de réponse en millisecondes',
    error_message TEXT NULL COMMENT 'Message d erreur si applicable',
    notification_sent BOOLEAN DEFAULT FALSE COMMENT 'Notification Discord envoyée',
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_domain_id (domain_id),
    INDEX idx_checked_at (checked_at),
    INDEX idx_status_found (status_found),

    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABLE: notifications
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_id INT NOT NULL,
    webhook_response TEXT NULL COMMENT 'Réponse brute du webhook Discord',
    http_status INT NULL COMMENT 'Code HTTP retourné',
    success BOOLEAN DEFAULT FALSE COMMENT 'Envoi réussi ou non',
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_domain_id (domain_id),
    INDEX idx_sent_at (sent_at),
    INDEX idx_success (success),

    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PROCÉDURE: Nettoyage des vieux logs (> 30 jours)
-- ============================================
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS cleanup_old_logs()
BEGIN
    DELETE FROM check_logs WHERE checked_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
    DELETE FROM notifications WHERE sent_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
END //
DELIMITER ;

-- ============================================
-- EVENT: Nettoyage automatique quotidien
-- ============================================
SET GLOBAL event_scheduler = ON;

CREATE EVENT IF NOT EXISTS daily_cleanup
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO CALL cleanup_old_logs();
