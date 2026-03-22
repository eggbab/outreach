class TestKeywords:
    def test_add_keyword(self, client, auth_headers, project_id):
        response = client.post(
            f"/api/projects/{project_id}/keywords/",
            json={"keyword": "B2B sales", "source": "naver"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["keyword"] == "B2B sales"
        assert data["source"] == "naver"
        assert "id" in data
        assert "created_at" in data

    def test_list_keywords(self, client, auth_headers, project_id):
        # Add two keywords
        client.post(
            f"/api/projects/{project_id}/keywords/",
            json={"keyword": "keyword1", "source": "naver"},
            headers=auth_headers,
        )
        client.post(
            f"/api/projects/{project_id}/keywords/",
            json={"keyword": "keyword2", "source": "google"},
            headers=auth_headers,
        )

        response = client.get(
            f"/api/projects/{project_id}/keywords/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        keywords = {kw["keyword"] for kw in data}
        assert "keyword1" in keywords
        assert "keyword2" in keywords

    def test_delete_keyword(self, client, auth_headers, project_id):
        # Create a keyword
        resp = client.post(
            f"/api/projects/{project_id}/keywords/",
            json={"keyword": "to_delete", "source": "naver"},
            headers=auth_headers,
        )
        keyword_id = resp.json()["id"]

        # Delete it
        response = client.delete(
            f"/api/projects/{project_id}/keywords/{keyword_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(
            f"/api/projects/{project_id}/keywords/",
            headers=auth_headers,
        )
        assert len(response.json()) == 0
