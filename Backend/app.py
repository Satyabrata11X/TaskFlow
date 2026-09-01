"""
TaskFlow Flask Application
Main entry point for serving frontend templates and REST API endpoints.
Implements Demo Authentication, RBAC, SQLite Integration, and Activity Logging.
"""

import os
from functools import wraps
from flask import Flask, jsonify, render_template, request, session
from database import get_db_connection, init_db

# Base directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "..", "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static"
)

# Secret key for Flask session management
app.secret_key = "taskflow_authsphere_demo_secret_key_super_safe"


# ============================================================
# RBAC PERMISSIONS MATRIX
# ============================================================
ROLE_PERMISSIONS = {
    "Owner": [
        "dashboard:view",
        "projects:view",
        "projects:create",
        "projects:edit",
        "projects:delete",
        "tasks:view",
        "tasks:create",
        "tasks:edit",
        "tasks:delete",
        "tasks:assign",
        "team:view",
        "users:view",
    ],
    "Manager": [
        "dashboard:view",
        "projects:view",
        "projects:create",
        "projects:edit",
        "tasks:view",
        "tasks:create",
        "tasks:edit",
        "tasks:delete",
        "tasks:assign",
        "team:view",
        "users:view",
    ],
    "Developer": [
        "dashboard:view",
        "projects:view",
        "tasks:view",
        "tasks:update_status",
        "team:view",
        "users:view",
    ],
    "HR": [
        "dashboard:view",
        "team:view",
        "users:view",
    ],
}


# ============================================================
# AUTH & RBAC HELPERS
# ============================================================
def get_current_user():
    """
    Retrieves the currently authenticated user from session['user_id']
    joined with the organization name from SQLite.
    Returns dict or None.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db_connection()
    user = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role, u.organization_id, o.name AS organization
        FROM users u
        JOIN organizations o ON u.organization_id = o.id
        WHERE u.id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if user:
        return dict(user)
    return None


def require_auth(f):
    """Decorator to require an active session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized: Please log in."}), 401
        return f(user, *args, **kwargs)
    return decorated_function


def require_permission(permission):
    """
    Decorator to verify that the logged-in user's role has the required permission.
    Returns 403 Forbidden if denied.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Unauthorized: Please log in."}), 401

            user_role = user.get("role")
            allowed_permissions = ROLE_PERMISSIONS.get(user_role, [])

            if permission not in allowed_permissions:
                return jsonify({
                    "error": f"Forbidden: Role '{user_role}' lacks permission '{permission}'."
                }), 403

            return f(user, *args, **kwargs)
        return decorated_function
    return decorator


def log_activity(user_id, action, project_id=None, task_id=None):
    """Helper to record an activity entry in SQLite."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO activities (user_id, project_id, task_id, action)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, project_id, task_id, action),
    )
    conn.commit()
    conn.close()


# ============================================================
# TEMPLATE ROUTES (SERVES FRONTEND PAGES)
# ============================================================
@app.route("/")
def page_index():
    return render_template("index.html")


@app.route("/login.html")
@app.route("/login")
def page_login():
    return render_template("login.html")


@app.route("/dashboard.html")
@app.route("/dashboard")
def page_dashboard():
    return render_template("dashboard.html")


@app.route("/projects.html")
@app.route("/projects")
def page_projects():
    return render_template("projects.html")


@app.route("/tasks.html")
@app.route("/tasks")
def page_tasks():
    return render_template("tasks.html")


@app.route("/team.html")
@app.route("/team")
def page_team():
    return render_template("team.html")


# ============================================================
# SYSTEM & HEALTH APIs
# ============================================================
@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check endpoint validating SQLite connection."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/api/message", methods=["GET"])
def api_message():
    """System connection test message."""
    return jsonify({
        "message": "TaskFlow Flask backend is connected successfully."
    }), 200


# ============================================================
# AUTHENTICATION APIs
# ============================================================
@app.route("/api/me", methods=["GET"])
def api_me():
    """
    Returns current authenticated user details or 401 if unauthenticated.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "organization": user["organization"],
        "permissions": ROLE_PERMISSIONS.get(user["role"], [])
    }), 200


@app.route("/api/login", methods=["POST"])
def api_login():
    """
    Demo login endpoint: Sets Flask session for the selected user.
    Accepts JSON: {"user_id": 1} or Form Data.
    """
    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "User ID is required for demo login"}), 400

    conn = get_db_connection()
    user = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role, o.name as organization
        FROM users u
        JOIN organizations o ON u.organization_id = o.id
        WHERE u.id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    session["user_id"] = user["id"]

    return jsonify({
        "message": f"Successfully logged in as {user['name']}",
        "user": dict(user)
    }), 200


@app.route("/api/logout", methods=["GET", "POST"])
def api_logout():
    """Clears current Flask session."""
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


# ============================================================
# USERS & TEAM API
# ============================================================
@app.route("/api/users", methods=["GET"])
@require_auth
def api_users(current_user):
    """
    Returns all users belonging to the organization.
    """
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role, o.name AS organization, u.created_at
        FROM users u
        JOIN organizations o ON u.organization_id = o.id
        WHERE u.organization_id = ?
        ORDER BY u.id ASC
        """,
        (current_user["organization_id"],),
    ).fetchall()
    conn.close()

    users = [dict(row) for row in rows]
    return jsonify(users), 200


# ============================================================
# DASHBOARD API
# ============================================================
@app.route("/api/dashboard", methods=["GET"])
@require_auth
def api_dashboard(current_user):
    """
    Returns live metrics, recent projects, and recent activity from SQLite.
    """
    conn = get_db_connection()
    org_id = current_user["organization_id"]

    # 1. Total Projects
    total_projects_row = conn.execute(
        "SELECT COUNT(*) as count FROM projects WHERE organization_id = ?",
        (org_id,),
    ).fetchone()
    total_projects = total_projects_row["count"] if total_projects_row else 0

    # 2. Active Tasks (status != 'Completed')
    active_tasks_row = conn.execute(
        """
        SELECT COUNT(*) as count FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE p.organization_id = ? AND t.status != 'Completed'
        """,
        (org_id,),
    ).fetchone()
    active_tasks = active_tasks_row["count"] if active_tasks_row else 0

    # 3. Total Tasks & Completed Tasks for percentage calculation
    total_tasks_row = conn.execute(
        """
        SELECT COUNT(*) as count FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE p.organization_id = ?
        """,
        (org_id,),
    ).fetchone()
    total_tasks = total_tasks_row["count"] if total_tasks_row else 0

    completed_tasks_row = conn.execute(
        """
        SELECT COUNT(*) as count FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE p.organization_id = ? AND t.status = 'Completed'
        """,
        (org_id,),
    ).fetchone()
    completed_tasks = completed_tasks_row["count"] if completed_tasks_row else 0

    if total_tasks > 0:
        completed_percentage = int(round((completed_tasks / total_tasks) * 100))
    else:
        completed_percentage = 0

    # 4. Team Members
    team_members_row = conn.execute(
        "SELECT COUNT(*) as count FROM users WHERE organization_id = ?",
        (org_id,),
    ).fetchone()
    team_members = team_members_row["count"] if team_members_row else 0

    # 5. Recent Projects (up to 5)
    recent_projects_rows = conn.execute(
        """
        SELECT p.id, p.name, p.description, p.status, p.progress, p.created_at,
               (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.id) AS member_count,
               (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) AS task_count
        FROM projects p
        WHERE p.organization_id = ?
        ORDER BY p.id DESC
        LIMIT 5
        """,
        (org_id,),
    ).fetchall()
    recent_projects = [dict(r) for r in recent_projects_rows]

    # 6. Recent Activities (up to 10)
    recent_activities_rows = conn.execute(
        """
        SELECT a.id, a.action, a.created_at, u.name AS user_name, u.role AS user_role,
               p.name AS project_name, t.title AS task_title
        FROM activities a
        JOIN users u ON a.user_id = u.id
        LEFT JOIN projects p ON a.project_id = p.id
        LEFT JOIN tasks t ON a.task_id = t.id
        WHERE u.organization_id = ?
        ORDER BY a.id DESC
        LIMIT 10
        """,
        (org_id,),
    ).fetchall()
    recent_activities = [dict(r) for r in recent_activities_rows]

    conn.close()

    return jsonify({
        "total_projects": total_projects,
        "active_tasks": active_tasks,
        "team_members": team_members,
        "completed_percentage": completed_percentage,
        "recent_projects": recent_projects,
        "recent_activities": recent_activities,
    }), 200


# ============================================================
# PROJECTS API
# ============================================================
@app.route("/api/projects", methods=["GET"])
@require_auth
def api_get_projects(current_user):
    """
    Returns list of all projects for the organization with member names & task statistics.
    """
    conn = get_db_connection()
    projects_rows = conn.execute(
        """
        SELECT p.id, p.name, p.description, p.status, p.progress, p.created_at, p.organization_id
        FROM projects p
        WHERE p.organization_id = ?
        ORDER BY p.id DESC
        """,
        (current_user["organization_id"],),
    ).fetchall()

    projects = []
    for row in projects_rows:
        proj = dict(row)

        # Fetch project members
        members_rows = conn.execute(
            """
            SELECT u.id, u.name, u.role, u.email
            FROM users u
            JOIN project_members pm ON u.id = pm.user_id
            WHERE pm.project_id = ?
            """,
            (proj["id"],),
        ).fetchall()
        proj["members"] = [dict(m) for m in members_rows]

        # Fetch task counts
        task_stats = conn.execute(
            """
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM tasks
            WHERE project_id = ?
            """,
            (proj["id"],),
        ).fetchone()

        proj["total_tasks"] = task_stats["total_tasks"] if task_stats else 0
        proj["completed_tasks"] = task_stats["completed_tasks"] or 0 if task_stats else 0

        projects.append(proj)

    conn.close()
    return jsonify(projects), 200


@app.route("/api/projects", methods=["POST"])
@require_permission("projects:create")
def api_create_project(current_user):
    """
    Creates a new project. Permitted for: Owner, Manager.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Project name is required"}), 400

    description = data.get("description", "").strip()
    status = data.get("status", "Active")
    if status not in ["Planning", "Active", "Completed"]:
        status = "Active"

    try:
        progress = int(data.get("progress", 0))
        progress = max(0, min(100, progress))
    except (ValueError, TypeError):
        progress = 0

    member_ids = data.get("member_ids", [])

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO projects (name, description, status, progress, organization_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, description, status, progress, current_user["organization_id"]),
    )
    new_project_id = cursor.lastrowid

    # Automatically add creator and requested members
    all_members = set(member_ids)
    all_members.add(current_user["id"])

    for u_id in all_members:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?, ?)",
                (new_project_id, int(u_id)),
            )
        except Exception:
            pass

    # Log activity
    cursor.execute(
        """
        INSERT INTO activities (user_id, project_id, action)
        VALUES (?, ?, ?)
        """,
        (current_user["id"], new_project_id, f"created project '{name}'"),
    )

    conn.commit()

    # Fetch created project
    created = cursor.execute("SELECT * FROM projects WHERE id = ?", (new_project_id,)).fetchone()
    conn.close()

    return jsonify(dict(created)), 201


@app.route("/api/projects/<int:project_id>", methods=["PUT"])
@require_permission("projects:edit")
def api_update_project(current_user, project_id):
    """
    Updates an existing project. Permitted for: Owner, Manager.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT * FROM projects WHERE id = ? AND organization_id = ?",
        (project_id, current_user["organization_id"]),
    ).fetchone()

    if not existing:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    name = data.get("name", existing["name"]).strip()
    description = data.get("description", existing["description"])
    status = data.get("status", existing["status"])
    if status not in ["Planning", "Active", "Completed"]:
        status = existing["status"]

    try:
        progress = int(data.get("progress", existing["progress"]))
        progress = max(0, min(100, progress))
    except (ValueError, TypeError):
        progress = existing["progress"]

    cursor.execute(
        """
        UPDATE projects
        SET name = ?, description = ?, status = ?, progress = ?
        WHERE id = ?
        """,
        (name, description, status, progress, project_id),
    )

    if "member_ids" in data:
        cursor.execute("DELETE FROM project_members WHERE project_id = ?", (project_id,))
        for u_id in data["member_ids"]:
            cursor.execute(
                "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?, ?)",
                (project_id, int(u_id)),
            )

    # Log activity
    cursor.execute(
        """
        INSERT INTO activities (user_id, project_id, action)
        VALUES (?, ?, ?)
        """,
        (current_user["id"], project_id, f"updated project '{name}'"),
    )

    conn.commit()
    updated = cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()

    return jsonify(dict(updated)), 200


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
@require_permission("projects:delete")
def api_delete_project(current_user, project_id):
    """
    Deletes a project. Permitted ONLY for: Owner.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT * FROM projects WHERE id = ? AND organization_id = ?",
        (project_id, current_user["organization_id"]),
    ).fetchone()

    if not existing:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    project_name = existing["name"]

    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    # Log activity (set project_id to None since it is deleted)
    cursor.execute(
        """
        INSERT INTO activities (user_id, project_id, action)
        VALUES (?, NULL, ?)
        """,
        (current_user["id"], f"deleted project '{project_name}'"),
    )

    conn.commit()
    conn.close()

    return jsonify({"message": f"Project '{project_name}' deleted successfully"}), 200


# ============================================================
# TASKS API
# ============================================================
@app.route("/api/tasks", methods=["GET"])
@require_auth
def api_get_tasks(current_user):
    """
    Returns tasks for the organization, joined with project name and assignee name.
    """
    conn = get_db_connection()
    project_id = request.args.get("project_id")
    status = request.args.get("status")

    query = """
        SELECT t.id, t.title, t.description, t.status, t.project_id, t.assigned_to, t.created_at,
               p.name AS project_name, u.name AS assignee_name, u.role AS assignee_role
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE p.organization_id = ?
    """
    params = [current_user["organization_id"]]

    if project_id:
        query += " AND t.project_id = ?"
        params.append(project_id)

    if status and status != "All":
        query += " AND t.status = ?"
        params.append(status)

    query += " ORDER BY t.id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    tasks = [dict(r) for r in rows]
    return jsonify(tasks), 200


@app.route("/api/tasks", methods=["POST"])
@require_permission("tasks:create")
def api_create_task(current_user):
    """
    Creates a new task. Permitted for: Owner, Manager.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Task title is required"}), 400

    description = data.get("description", "").strip()
    status = data.get("status", "Todo")
    if status not in ["Todo", "In Progress", "Completed"]:
        status = "Todo"

    project_id = data.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    assigned_to = data.get("assigned_to")
    if assigned_to:
        try:
            assigned_to = int(assigned_to)
        except ValueError:
            assigned_to = None

    conn = get_db_connection()
    cursor = conn.cursor()

    # Validate project belongs to user's organization
    project = cursor.execute(
        "SELECT * FROM projects WHERE id = ? AND organization_id = ?",
        (project_id, current_user["organization_id"]),
    ).fetchone()

    if not project:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    cursor.execute(
        """
        INSERT INTO tasks (title, description, status, project_id, assigned_to)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, description, status, project_id, assigned_to),
    )
    new_task_id = cursor.lastrowid

    # Log activity
    cursor.execute(
        """
        INSERT INTO activities (user_id, project_id, task_id, action)
        VALUES (?, ?, ?, ?)
        """,
        (current_user["id"], project_id, new_task_id, f"created task '{title}'"),
    )

    conn.commit()
    created = cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_task_id,)).fetchone()
    conn.close()

    return jsonify(dict(created)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@require_auth
def api_update_task(current_user, task_id):
    """
    Updates a task.
    - Owner and Manager: can update all fields (title, description, status, assigned_to).
    - Developer: can update task status.
    - HR: Forbidden (403).
    """
    user_role = current_user["role"]

    if user_role == "HR":
        return jsonify({"error": "Forbidden: HR cannot update tasks"}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    task = cursor.execute(
        """
        SELECT t.*, p.organization_id
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ? AND p.organization_id = ?
        """,
        (task_id, current_user["organization_id"]),
    ).fetchone()

    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json()
    if not data:
        conn.close()
        return jsonify({"error": "Missing JSON request body"}), 400

    new_status = data.get("status", task["status"])
    if new_status not in ["Todo", "In Progress", "Completed"]:
        new_status = task["status"]

    if user_role == "Developer":
        # Developer can only update status
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (new_status, task_id),
        )
        action_msg = f"updated task '{task['title']}' status to {new_status}"
    else:
        # Owner & Manager can update title, description, status, assigned_to
        title = data.get("title", task["title"]).strip()
        description = data.get("description", task["description"])
        assigned_to = data.get("assigned_to", task["assigned_to"])
        if assigned_to:
            try:
                assigned_to = int(assigned_to)
            except ValueError:
                assigned_to = None

        cursor.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, status = ?, assigned_to = ?
            WHERE id = ?
            """,
            (title, description, new_status, assigned_to, task_id),
        )
        action_msg = f"updated task '{title}'"

    # Log activity
    cursor.execute(
        """
        INSERT INTO activities (user_id, project_id, task_id, action)
        VALUES (?, ?, ?, ?)
        """,
        (current_user["id"], task["project_id"], task_id, action_msg),
    )

    conn.commit()
    updated = cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()

    return jsonify(dict(updated)), 200


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@require_permission("tasks:delete")
def api_delete_task(current_user, task_id):
    """
    Deletes a task. Permitted for: Owner, Manager.
    Developer and HR receive 403 Forbidden.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    task = cursor.execute(
        """
        SELECT t.*, p.organization_id
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ? AND p.organization_id = ?
        """,
        (task_id, current_user["organization_id"]),
    ).fetchone()

    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    task_title = task["title"]
    project_id = task["project_id"]

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    # Log activity
    cursor.execute(
        """
        INSERT INTO activities (user_id, project_id, action)
        VALUES (?, ?, ?)
        """,
        (current_user["id"], project_id, f"deleted task '{task_title}'"),
    )

    conn.commit()
    conn.close()

    return jsonify({"message": f"Task '{task_title}' deleted successfully"}), 200


# ============================================================
# ERROR HANDLERS (RETURN JSON ONLY)
# ============================================================
@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": "Bad Request"}), 400


@app.errorhandler(401)
def handle_unauthorized(e):
    return jsonify({"error": "Unauthorized"}), 401


@app.errorhandler(403)
def handle_forbidden(e):
    return jsonify({"error": "Forbidden"}), 403


@app.errorhandler(404)
def handle_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("index.html"), 404


@app.errorhandler(500)
def handle_server_error(e):
    return jsonify({"error": "Internal Server Error"}), 500


# ============================================================
# SERVER BOOTSTRAP
# ============================================================
if __name__ == "__main__":
    db_file = os.path.join(BASE_DIR, "taskflow.db")
    if not os.path.exists(db_file):
        print("[!] taskflow.db not found. Initializing database schema...")
        init_db()

    print("[*] Starting TaskFlow Flask Server on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)
