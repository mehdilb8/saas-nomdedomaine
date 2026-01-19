// API Configuration
const API_BASE_URL = window.location.origin;
const API_URL = `${API_BASE_URL}/api`;

// State
let currentDomains = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadDomains();
    setupEventListeners();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadDomains();
    }, 30000);
});

// Event Listeners
function setupEventListeners() {
    // Add domain form
    document.getElementById('addDomainForm').addEventListener('submit', handleAddDomain);

    // Edit domain form
    document.getElementById('editDomainForm').addEventListener('submit', handleEditDomain);

    // Filters
    document.getElementById('filterStatus').addEventListener('change', loadDomains);
    document.getElementById('filterMonitoring').addEventListener('change', loadDomains);
    document.getElementById('searchDomain').addEventListener('input', debounce(loadDomains, 500));

    // Close modal on outside click
    document.getElementById('editModal').addEventListener('click', (e) => {
        if (e.target.id === 'editModal') {
            closeEditModal();
        }
    });
}

// Load Statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();

        document.getElementById('totalDomains').textContent = data.total_domains || 0;
        document.getElementById('availableDomains').textContent = data.available_domains || 0;
        document.getElementById('activeWatchers').textContent = data.active_watchers || 0;
        document.getElementById('totalChecks').textContent = data.total_checks || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load Domains
async function loadDomains() {
    const container = document.getElementById('domainsContainer');
    const loading = document.getElementById('loadingSpinner');

    loading.style.display = 'block';
    container.innerHTML = '';

    try {
        // Build query parameters
        const params = new URLSearchParams();

        const status = document.getElementById('filterStatus').value;
        if (status) params.append('status', status);

        const monitoring = document.getElementById('filterMonitoring').value;
        if (monitoring) params.append('monitoring_active', monitoring);

        const search = document.getElementById('searchDomain').value;
        if (search) params.append('search', search);

        params.append('limit', '100');

        const response = await fetch(`${API_URL}/domains?${params}`);
        const data = await response.json();

        currentDomains = data.domains || [];

        loading.style.display = 'none';

        if (currentDomains.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-title">Aucun domaine trouvé</div>
                    <div class="empty-state-text">Ajoutez votre premier domaine pour commencer la surveillance</div>
                </div>
            `;
            return;
        }

        currentDomains.forEach(domain => {
            container.appendChild(createDomainCard(domain));
        });

    } catch (error) {
        loading.style.display = 'none';
        showToast('Erreur lors du chargement des domaines', 'error');
        console.error('Error loading domains:', error);
    }
}

// Create Domain Card
function createDomainCard(domain) {
    const card = document.createElement('div');
    card.className = 'domain-card';

    const statusBadge = getStatusBadge(domain.status);
    const monitoringBadge = domain.monitoring_active
        ? '<span class="badge badge-info">Surveillance active</span>'
        : '<span class="badge badge-gray">Surveillance inactive</span>';

    const lastCheck = domain.last_check_at
        ? new Date(domain.last_check_at).toLocaleString('fr-FR')
        : 'Jamais';

    card.innerHTML = `
        <div class="domain-header">
            <div class="domain-title">
                <span class="domain-name">${domain.domain}</span>
                ${statusBadge}
                ${monitoringBadge}
            </div>
            <div class="domain-actions">
                <button class="btn btn-small btn-primary" onclick="checkDomain(${domain.id})">
                    🔄 Vérifier
                </button>
                <button class="btn btn-small btn-secondary" onclick="toggleMonitoring(${domain.id}, ${domain.monitoring_active})">
                    ${domain.monitoring_active ? '⏸️ Pause' : '▶️ Activer'}
                </button>
                <button class="btn btn-small btn-secondary" onclick="openEditModal(${domain.id})">
                    ✏️ Modifier
                </button>
                <button class="btn btn-small btn-danger" onclick="deleteDomain(${domain.id}, '${domain.domain}')">
                    🗑️ Supprimer
                </button>
            </div>
        </div>
        <div class="domain-info">
            <div class="info-item">
                <span class="info-label">TLD</span>
                <span class="info-value">${domain.tld || '-'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Niche</span>
                <span class="info-value">${domain.niche || '-'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Trafic</span>
                <span class="info-value">${domain.traffic ? domain.traffic.toLocaleString() : '-'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Domaines référents</span>
                <span class="info-value">${domain.referring_domains || '-'}</span>
            </div>
        </div>
        <div class="domain-footer">
            <span>Dernière vérification: ${lastCheck}</span>
            <span>Ajouté le: ${new Date(domain.created_at).toLocaleDateString('fr-FR')}</span>
        </div>
    `;

    return card;
}

// Get Status Badge
function getStatusBadge(status) {
    const badges = {
        'available': '<span class="badge badge-success">✅ Disponible</span>',
        'unavailable': '<span class="badge badge-danger">❌ Indisponible</span>',
        'unknown': '<span class="badge badge-warning">❓ Inconnu</span>'
    };
    return badges[status] || badges['unknown'];
}

// Add Domain
async function handleAddDomain(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        domain: formData.get('domain'),
        niche: formData.get('niche') || null,
        traffic: formData.get('traffic') ? parseInt(formData.get('traffic')) : null,
        referring_domains: formData.get('referring_domains') ? parseInt(formData.get('referring_domains')) : null
    };

    try {
        const response = await fetch(`${API_URL}/domains`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors de l\'ajout du domaine');
        }

        showToast('Domaine ajouté avec succès', 'success');
        e.target.reset();
        loadStats();
        loadDomains();

    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error adding domain:', error);
    }
}

// Check Domain
async function checkDomain(id) {
    try {
        showToast('Vérification en cours...', 'info');

        const response = await fetch(`${API_URL}/domains/${id}/check`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Erreur lors de la vérification');
        }

        const result = await response.json();
        showToast(`Vérification terminée: ${result.status}`, 'success');
        loadStats();
        loadDomains();

    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error checking domain:', error);
    }
}

// Toggle Monitoring
async function toggleMonitoring(id, currentState) {
    try {
        const response = await fetch(`${API_URL}/domains/${id}/toggle`, {
            method: 'PATCH'
        });

        if (!response.ok) {
            throw new Error('Erreur lors de la modification');
        }

        const newState = !currentState;
        showToast(
            newState ? 'Surveillance activée' : 'Surveillance désactivée',
            'success'
        );
        loadDomains();

    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error toggling monitoring:', error);
    }
}

// Open Edit Modal
function openEditModal(id) {
    const domain = currentDomains.find(d => d.id === id);
    if (!domain) return;

    document.getElementById('editDomainId').value = domain.id;
    document.getElementById('editDomain').value = domain.domain;
    document.getElementById('editNiche').value = domain.niche || '';
    document.getElementById('editTraffic').value = domain.traffic || '';
    document.getElementById('editReferringDomains').value = domain.referring_domains || '';

    document.getElementById('editModal').classList.add('show');
}

// Close Edit Modal
function closeEditModal() {
    document.getElementById('editModal').classList.remove('show');
    document.getElementById('editDomainForm').reset();
}

// Handle Edit Domain
async function handleEditDomain(e) {
    e.preventDefault();

    const id = document.getElementById('editDomainId').value;
    const formData = new FormData(e.target);

    const data = {
        niche: formData.get('niche') || null,
        traffic: formData.get('traffic') ? parseInt(formData.get('traffic')) : null,
        referring_domains: formData.get('referring_domains') ? parseInt(formData.get('referring_domains')) : null
    };

    try {
        const response = await fetch(`${API_URL}/domains/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Erreur lors de la modification');
        }

        showToast('Domaine modifié avec succès', 'success');
        closeEditModal();
        loadDomains();

    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error editing domain:', error);
    }
}

// Delete Domain
async function deleteDomain(id, domainName) {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer "${domainName}" ?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/domains/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Erreur lors de la suppression');
        }

        showToast('Domaine supprimé avec succès', 'success');
        loadStats();
        loadDomains();

    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error deleting domain:', error);
    }
}

// Show Toast Notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };

    toast.innerHTML = `
        <span>${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
