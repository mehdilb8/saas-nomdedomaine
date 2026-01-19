"""
Tests for API Endpoints
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Test health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test GET /api/health"""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data


class TestStatsEndpoint:
    """Test statistics endpoint"""

    @pytest.mark.asyncio
    async def test_get_stats(self, client: AsyncClient):
        """Test GET /api/stats"""
        response = await client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_domains" in data
        assert "active_domains" in data
        assert "by_status" in data
        assert "by_tld" in data


class TestDomainCRUD:
    """Test domain CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_domain(self, client: AsyncClient):
        """Test POST /api/domains"""
        payload = {
            "domain": "test-domain.fr",
            "niche": "Tech",
            "traffic": 1000,
            "referring_domains": 50
        }

        response = await client.post("/api/domains", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["domain"] == "test-domain.fr"
        assert data["tld"] == "fr"
        assert data["niche"] == "Tech"
        assert data["traffic"] == 1000

    @pytest.mark.asyncio
    async def test_create_domain_unsupported_tld(self, client: AsyncClient):
        """Test POST /api/domains with unsupported TLD"""
        payload = {
            "domain": "test-domain.org",
            "niche": "Tech"
        }

        response = await client.post("/api/domains", json=payload)

        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_domains(self, client: AsyncClient, sample_domain):
        """Test GET /api/domains"""
        response = await client.get("/api/domains")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "domains" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_domain_by_id(self, client: AsyncClient, sample_domain):
        """Test GET /api/domains/{id}"""
        response = await client.get(f"/api/domains/{sample_domain.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_domain.id
        assert data["domain"] == sample_domain.domain
        assert "recent_checks" in data

    @pytest.mark.asyncio
    async def test_get_domain_not_found(self, client: AsyncClient):
        """Test GET /api/domains/{id} with invalid ID"""
        response = await client.get("/api/domains/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_domain(self, client: AsyncClient, sample_domain):
        """Test PUT /api/domains/{id}"""
        payload = {
            "niche": "Finance",
            "traffic": 10000
        }

        response = await client.put(f"/api/domains/{sample_domain.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["niche"] == "Finance"
        assert data["traffic"] == 10000

    @pytest.mark.asyncio
    async def test_toggle_monitoring(self, client: AsyncClient, sample_domain):
        """Test PATCH /api/domains/{id}/toggle"""
        initial_status = sample_domain.is_active

        response = await client.patch(f"/api/domains/{sample_domain.id}/toggle")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] != initial_status

    @pytest.mark.asyncio
    async def test_delete_domain(self, client: AsyncClient, sample_domain):
        """Test DELETE /api/domains/{id}"""
        response = await client.delete(f"/api/domains/{sample_domain.id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(f"/api/domains/{sample_domain.id}")
        assert get_response.status_code == 404


class TestDomainFilters:
    """Test domain filtering and pagination"""

    @pytest.mark.asyncio
    async def test_filter_by_tld(self, client: AsyncClient, sample_domain):
        """Test GET /api/domains?tld=fr"""
        response = await client.get("/api/domains?tld=fr")

        assert response.status_code == 200
        data = response.json()
        for domain in data["domains"]:
            assert domain["tld"] == "fr"

    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient, sample_domain):
        """Test GET /api/domains with pagination"""
        response = await client.get("/api/domains?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["domains"]) <= 10
