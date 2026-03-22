from app.models.models import Prospect


class TestProspects:
    def test_list_prospects_empty(self, client, auth_headers, project_id):
        response = client.get(
            f"/api/projects/{project_id}/prospects/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_prospects_pagination_format(self, client, auth_headers, project_id, db_session):
        # Insert prospects directly into DB
        for i in range(3):
            prospect = Prospect(
                project_id=project_id,
                name=f"Prospect {i}",
                email=f"p{i}@example.com",
                source="naver",
                status="collected",
            )
            db_session.add(prospect)
        db_session.commit()

        response = client.get(
            f"/api/projects/{project_id}/prospects/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "total_pages" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] == 3
        assert data["total_pages"] == 1
        assert len(data["items"]) == 3

    def test_approve_prospect(self, client, auth_headers, project_id, db_session):
        prospect = Prospect(
            project_id=project_id,
            name="To Approve",
            email="approve@example.com",
            source="naver",
            status="collected",
        )
        db_session.add(prospect)
        db_session.commit()
        db_session.refresh(prospect)

        response = client.patch(
            f"/api/projects/{project_id}/prospects/{prospect.id}",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

    def test_approve_all(self, client, auth_headers, project_id, db_session):
        # Insert multiple collected prospects
        for i in range(5):
            db_session.add(
                Prospect(
                    project_id=project_id,
                    name=f"Prospect {i}",
                    source="naver",
                    status="collected",
                )
            )
        # One already approved — should not be counted
        db_session.add(
            Prospect(
                project_id=project_id,
                name="Already Approved",
                source="naver",
                status="approved",
            )
        )
        db_session.commit()

        response = client.post(
            f"/api/projects/{project_id}/prospects/approve-all",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["approved_count"] == 5
