from app.models.models import EmailLog, DmLog, Prospect


class TestDashboard:
    def test_dashboard_stats_empty(self, client, auth_headers):
        response = client.get("/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 0
        assert data["total_prospects"] == 0
        assert data["emails_sent"] == 0
        assert data["dms_sent"] == 0

    def test_dashboard_stats_with_data(self, client, auth_headers, project_id, db_session):
        # Get user id from /me
        me = client.get("/api/auth/me", headers=auth_headers).json()
        user_id = me["id"]

        # Add prospects
        prospects = []
        for i in range(3):
            p = Prospect(
                project_id=project_id,
                name=f"P{i}",
                email=f"p{i}@example.com",
                source="naver",
                status="collected",
            )
            db_session.add(p)
            db_session.flush()
            prospects.append(p)

        # Add email log (success)
        db_session.add(
            EmailLog(
                prospect_id=prospects[0].id,
                user_id=user_id,
                status="success",
            )
        )
        # Add email log (failed — should not count)
        db_session.add(
            EmailLog(
                prospect_id=prospects[1].id,
                user_id=user_id,
                status="failed",
            )
        )
        # Add DM log (success)
        db_session.add(
            DmLog(
                prospect_id=prospects[2].id,
                user_id=user_id,
                status="success",
            )
        )
        db_session.commit()

        response = client.get("/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 1
        assert data["total_prospects"] == 3
        assert data["emails_sent"] == 1
        assert data["dms_sent"] == 1
