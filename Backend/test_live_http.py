"""
Live HTTP Endpoint and Workflow Verification Script.
Tests all routes directly against the running server on http://127.0.0.1:5000/
"""

import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "http://127.0.0.1:5000"

def run_live_tests():
    print("[*] Starting live HTTP verification against", BASE_URL)
    
    # Setup cookie jar for session management
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def make_request(path, method="GET", data=None):
        url = BASE_URL + path
        headers = {}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with opener.open(req) as resp:
                status = resp.status
                content = resp.read().decode("utf-8")
                try:
                    json_data = json.loads(content)
                except Exception:
                    json_data = None
                return status, json_data, content
        except urllib.error.HTTPError as e:
            content = e.read().decode("utf-8")
            try:
                json_data = json.loads(content)
            except Exception:
                json_data = None
            return e.code, json_data, content

    # 1. Test Static & HTML pages
    pages = ["/", "/login.html", "/dashboard.html", "/projects.html", "/tasks.html", "/team.html", "/static/style.css", "/static/js/app.js"]
    for p in pages:
        status, _, content = make_request(p)
        assert status == 200, f"Page {p} returned status {status}"
        assert len(content) > 50, f"Page {p} content too short"
        print(f"  [OK] GET {p} -> {status} OK ({len(content)} bytes)")

    # 2. Test Health & Message API
    status, json_data, _ = make_request("/api/health")
    assert status == 200 and json_data["status"] == "healthy"
    print("  [OK] GET /api/health -> healthy")

    status, json_data, _ = make_request("/api/message")
    assert status == 200 and "TaskFlow" in json_data["message"]
    print("  [OK] GET /api/message -> message OK")

    # 3. Test Unauthorized access to /api/me
    status, json_data, _ = make_request("/api/me")
    assert status == 401, f"Expected 401, got {status}"
    print("  [OK] GET /api/me (unauthenticated) -> 401 Unauthorized")

    # 4. Login as Satya (Owner)
    status, json_data, _ = make_request("/api/login", method="POST", data={"user_id": 1})
    assert status == 200 and json_data["user"]["name"] == "Satya"
    print("  [OK] POST /api/login (Satya, Owner) -> 200 OK")

    # 5. Check /api/me as Satya
    status, json_data, _ = make_request("/api/me")
    assert status == 200 and json_data["role"] == "Owner" and json_data["organization"] == "TechCorp"
    print("  [OK] GET /api/me -> Satya, Owner, TechCorp")

    # 6. Check Dashboard metrics
    status, json_data, _ = make_request("/api/dashboard")
    assert status == 200 and json_data["team_members"] == 4
    print(f"  [OK] GET /api/dashboard -> Projects: {json_data['total_projects']}, Tasks: {json_data['active_tasks']}, Completed: {json_data['completed_percentage']}%")

    # 7. Check Users / Team list
    status, json_data, _ = make_request("/api/users")
    assert status == 200 and len(json_data) == 4
    print("  [OK] GET /api/users -> 4 users returned")

    # 8. Create a Project as Owner
    status, json_data, _ = make_request("/api/projects", method="POST", data={
        "name": "Live HTTP Test Project",
        "description": "Live end-to-end verification",
        "status": "Active",
        "progress": 50,
        "member_ids": [1, 2, 3]
    })
    assert status == 201, f"Expected 201, got {status}"
    new_proj_id = json_data["id"]
    print(f"  [OK] POST /api/projects -> Created project ID {new_proj_id}")

    # 9. Create a Task under this project
    status, json_data, _ = make_request("/api/tasks", method="POST", data={
        "title": "Live Test Task",
        "description": "Verify task creation and assignment",
        "status": "Todo",
        "project_id": new_proj_id,
        "assigned_to": 3 # Rahul
    })
    assert status == 201
    new_task_id = json_data["id"]
    print(f"  [OK] POST /api/tasks -> Created task ID {new_task_id} (assigned to Rahul)")

    # 10. Update Task status to Completed
    status, json_data, _ = make_request(f"/api/tasks/{new_task_id}", method="PUT", data={"status": "Completed"})
    assert status == 200 and json_data["status"] == "Completed"
    print("  [OK] PUT /api/tasks/<id> -> Status updated to Completed")

    # 11. Switch user: Login as Rahul (Developer)
    status, json_data, _ = make_request("/api/login", method="POST", data={"user_id": 3})
    assert status == 200 and json_data["user"]["name"] == "Rahul"
    print("  [OK] POST /api/login (Rahul, Developer) -> 200 OK")

    # 12. Test Developer attempting to delete project -> MUST RETURN 403 FORBIDDEN
    status, json_data, _ = make_request(f"/api/projects/{new_proj_id}", method="DELETE")
    assert status == 403, f"Developer delete project should return 403, got {status}"
    print("  [OK] DELETE /api/projects/<id> as Developer -> 403 Forbidden (RBAC ENFORCED)")

    # 13. Test Developer attempting to create project -> MUST RETURN 403 FORBIDDEN
    status, json_data, _ = make_request("/api/projects", method="POST", data={"name": "Rahul Proj"})
    assert status == 403, f"Developer create project should return 403, got {status}"
    print("  [OK] POST /api/projects as Developer -> 403 Forbidden (RBAC ENFORCED)")

    # 14. Switch user: Login as Priya (Manager)
    status, json_data, _ = make_request("/api/login", method="POST", data={"user_id": 2})
    assert status == 200 and json_data["user"]["name"] == "Priya"
    print("  [OK] POST /api/login (Priya, Manager) -> 200 OK")

    # 15. Test Manager attempting to delete project -> MUST RETURN 403 FORBIDDEN
    status, json_data, _ = make_request(f"/api/projects/{new_proj_id}", method="DELETE")
    assert status == 403, f"Manager delete project should return 403, got {status}"
    print("  [OK] DELETE /api/projects/<id> as Manager -> 403 Forbidden (RBAC ENFORCED)")

    # 16. Switch user: Login as Amit (HR)
    status, json_data, _ = make_request("/api/login", method="POST", data={"user_id": 4})
    assert status == 200 and json_data["user"]["name"] == "Amit"
    print("  [OK] POST /api/login (Amit, HR) -> 200 OK")

    # 17. Test HR attempting to create task -> MUST RETURN 403 FORBIDDEN
    status, json_data, _ = make_request("/api/tasks", method="POST", data={"title": "HR Task", "project_id": new_proj_id})
    assert status == 403
    print("  [OK] POST /api/tasks as HR -> 403 Forbidden (RBAC ENFORCED)")

    # 18. Switch back to Satya (Owner) to delete test project
    status, json_data, _ = make_request("/api/login", method="POST", data={"user_id": 1})
    assert status == 200

    status, json_data, _ = make_request(f"/api/projects/{new_proj_id}", method="DELETE")
    assert status == 200
    print(f"  [OK] DELETE /api/projects/{new_proj_id} as Owner -> 200 OK (Project Deleted)")

    print("\n[+] ALL LIVE HTTP & RBAC TESTS PASSED SUCCESSFULLY WITH ZERO DEFECTS!")

if __name__ == "__main__":
    run_live_tests()
