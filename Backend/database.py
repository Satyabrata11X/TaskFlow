"""
TaskFlow Database Module
Handles SQLite schema creation, connection management, and demo data seeding.
"""

import os
import sqlite3
from datetime import datetime

# Database file path located in the Backend directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskflow.db")


def get_db_connection():
    """
    Creates and returns a connection to the SQLite database.
    Enables foreign keys and returns rows as dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Initializes the database schema and seeds initial demo data.
    """
    # If existing DB exists, remove it for a completely fresh start
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"[+] Removed existing database at {DB_PATH}")
        except Exception as e:
            print(f"[!] Warning removing database: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()

    print("[+] Creating database schema...")

    # 1. Organizations table
    cursor.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('Owner', 'Manager', 'Developer', 'HR')),
            organization_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        );
    """)

    # 3. Projects table
    cursor.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Planning', 'Active', 'Completed')),
            progress INTEGER NOT NULL DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
            organization_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        );
    """)

    # 4. Project Members table
    cursor.execute("""
        CREATE TABLE project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, user_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # 5. Tasks table
    cursor.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Todo' CHECK(status IN ('Todo', 'In Progress', 'Completed')),
            project_id INTEGER NOT NULL,
            assigned_to INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
        );
    """)

    # 6. Activities table
    cursor.execute("""
        CREATE TABLE activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_id INTEGER,
            task_id INTEGER,
            action TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );
    """)

    print("[+] Seeding demo organization and users...")

    # Seed Organization: TechCorp
    cursor.execute("INSERT INTO organizations (name) VALUES (?)", ("TechCorp",))
    org_id = cursor.lastrowid

    # Seed Demo Users
    demo_users = [
        ("Satya", "satya@techcorp.demo", "Owner", org_id),
        ("Priya", "priya@techcorp.demo", "Manager", org_id),
        ("Rahul", "rahul@techcorp.demo", "Developer", org_id),
        ("Amit", "amit@techcorp.demo", "HR", org_id),
    ]

    user_ids = {}
    for name, email, role, o_id in demo_users:
        cursor.execute(
            "INSERT INTO users (name, email, role, organization_id) VALUES (?, ?, ?, ?)",
            (name, email, role, o_id),
        )
        user_ids[name] = cursor.lastrowid
        print(f"    - Created user: {name} ({role}) - {email}")

    print("[+] Seeding demo projects...")

    # Seed Project 1: Student Management System
    cursor.execute(
        """
        INSERT INTO projects (name, description, status, progress, organization_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Student Management System",
            "A comprehensive web portal for managing student enrollments, attendance, grades, and course materials.",
            "Active",
            60,
            org_id,
        ),
    )
    proj_sms_id = cursor.lastrowid

    # Seed Project Members for Student Management System (Satya, Priya, Rahul)
    for name in ["Satya", "Priya", "Rahul"]:
        cursor.execute(
            "INSERT INTO project_members (project_id, user_id) VALUES (?, ?)",
            (proj_sms_id, user_ids[name]),
        )

    print("[+] Seeding demo tasks...")

    # Seed Tasks for Student Management System
    demo_tasks = [
        (
            "Design database schema",
            "Create normalized SQLite tables and indexes for student records",
            "Completed",
            proj_sms_id,
            user_ids["Rahul"],
        ),
        (
            "Build authentication module",
            "Implement identity and role verification pipeline",
            "In Progress",
            proj_sms_id,
            user_ids["Rahul"],
        ),
        (
            "Create dashboard wireframes",
            "Design dashboard UI and statistics overview cards",
            "Todo",
            proj_sms_id,
            user_ids["Satya"],
        ),
        (
            "Setup CI/CD pipeline",
            "Automate testing and deployment scripts",
            "In Progress",
            proj_sms_id,
            user_ids["Priya"],
        ),
    ]

    for title, desc, status, p_id, assigned in demo_tasks:
        cursor.execute(
            """
            INSERT INTO tasks (title, description, status, project_id, assigned_to)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, desc, status, p_id, assigned),
        )

    print("[+] Seeding demo activities...")

    # Seed Activities
    initial_activities = [
        (user_ids["Satya"], proj_sms_id, None, "created project 'Student Management System'"),
        (user_ids["Rahul"], proj_sms_id, 1, "completed task 'Design database schema'"),
        (user_ids["Priya"], proj_sms_id, 4, "started task 'Setup CI/CD pipeline'"),
        (user_ids["Rahul"], proj_sms_id, 2, "updated task 'Build authentication module' to In Progress"),
    ]

    for u_id, p_id, t_id, action in initial_activities:
        cursor.execute(
            """
            INSERT INTO activities (user_id, project_id, task_id, action)
            VALUES (?, ?, ?, ?)
            """,
            (u_id, p_id, t_id, action),
        )

    conn.commit()
    conn.close()
    print("[+] Database initialized and seeded successfully in taskflow.db!")


if __name__ == "__main__":
    init_db()
