class TestProjects:
    def test_create_project(self, client, auth_headers):
        response = client.post(
            "/api/projects/",
            json={"name": "My Project"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Project"
        assert data["description"] is None
        assert data["status"] == "active"
        assert "id" in data

    def test_create_project_with_description(self, client, auth_headers):
        response = client.post(
            "/api/projects/",
            json={"name": "Described Project", "description": "A test description"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Described Project"
        assert data["description"] == "A test description"

    def test_list_projects(self, client, auth_headers):
        # Create two projects
        client.post(
            "/api/projects/",
            json={"name": "Project A"},
            headers=auth_headers,
        )
        client.post(
            "/api/projects/",
            json={"name": "Project B"},
            headers=auth_headers,
        )

        response = client.get("/api/projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {p["name"] for p in data}
        assert "Project A" in names
        assert "Project B" in names

    def test_get_project_detail(self, client, auth_headers, project_id):
        response = client.get(
            f"/api/projects/{project_id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"
        assert data["prospect_count"] == 0
        assert data["approved_count"] == 0
        assert data["email_sent_count"] == 0
        assert data["dm_sent_count"] == 0

    def test_delete_project(self, client, auth_headers, project_id):
        response = client.delete(
            f"/api/projects/{project_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(
            f"/api/projects/{project_id}", headers=auth_headers
        )
        assert response.status_code == 404
