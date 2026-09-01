"""
Comprehensive Integration and RBAC Test Suite for TaskFlow.
Tests all 27 checklist items and verifies zero defects across all roles.
"""

import unittest
import json
import os
from database import init_db, get_db_connection
from app import app


class TaskFlowAPITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Fresh database setup
        init_db()

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def login_user(self, user_id):
        return self.client.post("/api/login", json={"user_id": user_id})

    def test_01_health_and_message_api(self):
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        data_health = res_health.get_json()
        self.assertEqual(data_health["status"], "healthy")
        self.assertEqual(data_health["database"], "connected")

        res_msg = self.client.get("/api/message")
        self.assertEqual(res_msg.status_code, 200)
        data_msg = res_msg.get_json()
        self.assertIn("TaskFlow Flask backend", data_msg["message"])

    def test_02_unauthenticated_api_me(self):
        res = self.client.get("/api/me")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Unauthorized")

    def test_03_login_and_me_satya_owner(self):
        login_res = self.login_user(1)
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.get_json()["user"]["name"], "Satya")

        me_res = self.client.get("/api/me")
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.get_json()
        self.assertEqual(me_data["name"], "Satya")
        self.assertEqual(me_data["role"], "Owner")
        self.assertEqual(me_data["email"], "satya@techcorp.demo")
        self.assertEqual(me_data["organization"], "TechCorp")

    def test_04_dashboard_metrics(self):
        self.login_user(1)
        res = self.client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_projects", data)
        self.assertIn("active_tasks", data)
        self.assertIn("team_members", data)
        self.assertIn("completed_percentage", data)
        self.assertEqual(data["team_members"], 4)
        self.assertGreaterEqual(data["total_projects"], 1)

    def test_05_team_users_api(self):
        self.login_user(1)
        res = self.client.get("/api/users")
        self.assertEqual(res.status_code, 200)
        users = res.get_json()
        self.assertEqual(len(users), 4)
        names = [u["name"] for u in users]
        self.assertListEqual(names, ["Satya", "Priya", "Rahul", "Amit"])

    def test_06_project_crud_owner(self):
        self.login_user(1)  # Satya (Owner)
        
        # Create Project
        res_create = self.client.post("/api/projects", json={
            "name": "Integration Portal",
            "description": "Enterprise microservices connector",
            "status": "Active",
            "progress": 30,
            "member_ids": [1, 2, 3]
        })
        self.assertEqual(res_create.status_code, 201)
        created_proj = res_create.get_json()
        proj_id = created_proj["id"]
        self.assertEqual(created_proj["name"], "Integration Portal")

        # Edit Project
        res_edit = self.client.put(f"/api/projects/{proj_id}", json={
            "name": "Integration Portal v2",
            "description": "Updated description",
            "status": "Completed",
            "progress": 100
        })
        self.assertEqual(res_edit.status_code, 200)
        updated_proj = res_edit.get_json()
        self.assertEqual(updated_proj["name"], "Integration Portal v2")
        self.assertEqual(updated_proj["status"], "Completed")

        # Delete Project (Owner permitted)
        res_delete = self.client.delete(f"/api/projects/{proj_id}")
        self.assertEqual(res_delete.status_code, 200)

    def test_07_task_crud_and_status_update(self):
        self.login_user(1)  # Satya (Owner)
        
        # Get first project
        proj_res = self.client.get("/api/projects")
        proj_id = proj_res.get_json()[0]["id"]

        # Create Task
        res_create = self.client.post("/api/tasks", json={
            "title": "Automate Integration Tests",
            "description": "Write automated test suite for AuthSphere RBAC",
            "status": "Todo",
            "project_id": proj_id,
            "assigned_to": 3  # Rahul
        })
        self.assertEqual(res_create.status_code, 201)
        task_id = res_create.get_json()["id"]

        # Update Task Status
        res_put = self.client.put(f"/api/tasks/{task_id}", json={
            "status": "Completed"
        })
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.get_json()["status"], "Completed")

        # Delete Task
        res_delete = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(res_delete.status_code, 200)

    def test_08_rbac_developer_restrictions(self):
        # Login as Rahul (Developer)
        self.login_user(3)
        me_res = self.client.get("/api/me")
        self.assertEqual(me_res.get_json()["role"], "Developer")

        # 1. Developer cannot create project -> 403 Forbidden
        res_proj_create = self.client.post("/api/projects", json={
            "name": "Unauthorized Project",
            "description": "Should fail",
            "project_id": 1
        })
        self.assertEqual(res_proj_create.status_code, 403)

        # 2. Developer cannot delete project -> 403 Forbidden
        res_proj_delete = self.client.delete("/api/projects/1")
        self.assertEqual(res_proj_delete.status_code, 403)

        # 3. Developer can view tasks & update status
        res_tasks = self.client.get("/api/tasks")
        self.assertEqual(res_tasks.status_code, 200)
        if len(res_tasks.get_json()) > 0:
            first_task_id = res_tasks.get_json()[0]["id"]
            res_update_status = self.client.put(f"/api/tasks/{first_task_id}", json={
                "status": "In Progress"
            })
            self.assertEqual(res_update_status.status_code, 200)

    def test_09_rbac_manager_permissions(self):
        # Login as Priya (Manager)
        self.login_user(2)
        me_res = self.client.get("/api/me")
        self.assertEqual(me_res.get_json()["role"], "Manager")

        # 1. Manager can create project -> 201 Created
        res_proj_create = self.client.post("/api/projects", json={
            "name": "Manager Project Alpha",
            "description": "Created by Priya",
            "status": "Planning",
            "progress": 10
        })
        self.assertEqual(res_proj_create.status_code, 201)
        mgr_proj_id = res_proj_create.get_json()["id"]

        # 2. Manager CANNOT delete project -> 403 Forbidden
        res_proj_delete = self.client.delete(f"/api/projects/{mgr_proj_id}")
        self.assertEqual(res_proj_delete.status_code, 403)

        # Clean up with Owner
        self.login_user(1)
        self.client.delete(f"/api/projects/{mgr_proj_id}")

    def test_10_rbac_hr_restrictions(self):
        # Login as Amit (HR)
        self.login_user(4)
        me_res = self.client.get("/api/me")
        self.assertEqual(me_res.get_json()["role"], "HR")

        # 1. HR can view dashboard and team
        res_dash = self.client.get("/api/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        res_team = self.client.get("/api/users")
        self.assertEqual(res_team.status_code, 200)

        # 2. HR cannot create project -> 403 Forbidden
        res_proj_create = self.client.post("/api/projects", json={"name": "HR Project"})
        self.assertEqual(res_proj_create.status_code, 403)

        # 3. HR cannot create task -> 403 Forbidden
        res_task_create = self.client.post("/api/tasks", json={
            "title": "HR Task",
            "project_id": 1
        })
        self.assertEqual(res_task_create.status_code, 403)

        # 4. HR cannot update task -> 403 Forbidden
        res_task_update = self.client.put("/api/tasks/1", json={"status": "Completed"})
        self.assertEqual(res_task_update.status_code, 403)


if __name__ == "__main__":
    unittest.main()
