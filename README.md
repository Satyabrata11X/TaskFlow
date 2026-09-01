# TaskFlow

A lightweight project management demo application built to demonstrate
authentication, identity, organizations, roles, permissions, and
Role-Based Access Control (RBAC).

TaskFlow is designed as a demo application for the **AuthSphere** project.

---

## Overview

TaskFlow simulates a real-world application that requires user
authentication and authorization.

The application contains different users with different roles and
permissions.

The main idea is:

```text
User
  ↓
Authentication
  ↓
Identity
  ↓
Organization
  ↓
Role
  ↓
Permissions
  ↓
TaskFlow

```

In the current version, authentication is simulated locally.

In the future, the demo login will be replaced by AuthSphere.

Features
Dashboard
Total projects
Active tasks
Team members
Task completion percentage
Recent projects
Recent activity
Projects
Create projects
Edit projects
Delete projects
Search projects
Filter projects
Track project progress
Assign project members
Tasks
Create tasks
Edit tasks
Delete tasks
Assign tasks to users
Track task status
Track task completion
Team

### The demo contains multiple users with different roles:

User	Role
Satya	Owner
Priya	Manager
Rahul	Developer
Amit	HR

All users belong to the demo organization:

## TechCorp

Role-Based Access Control

TaskFlow demonstrates how different users can have different
permissions.

Owner

Can:

Manage projects
Manage tasks
Manage team
Delete projects
View the complete workspace
Manager

Can:

Manage projects
Manage tasks
Assign tasks
View team members
Developer

Can:

View projects
View tasks
Update assigned tasks
View team members

Developer users do not have owner-level management permissions.

HR

Can:

View users
View team information

HR users do not have project-management permissions.

Technology Stack
Frontend
HTML5
CSS3
Vanilla JavaScript
Backend
Python
Flask
Database
SQLite


## Running the Application
1. Open the project
cd TaskFlow
2. Enter the Backend directory
cd Backend
3. Initialize the database
python database.py
4. Start Flask
python app.py
5. Open the application
http://127.0.0.1:5000/
Demo Users

The application contains four demo users.

Satya
Role: Owner

Priya
Role: Manager

Rahul
Role: Developer

Amit
Role: HR

### Organization:

TechCorp

These users are used to demonstrate different authorization levels.

AuthSphere Integration

TaskFlow currently uses a simulated authentication mechanism.

The future architecture will replace the demo authentication with
AuthSphere.
```
Current
Demo Login
    ↓
Flask Session
    ↓
User
    ↓
Role
    ↓
Permissions
    ↓
TaskFlow
Future
AuthSphere
    ↓
Authentication
    ↓
Identity
    ↓
Organization
    ↓
Role
    ↓
Permissions
    ↓
TaskFlow
```

AuthSphere will eventually provide the authenticated user's identity,
organization context, roles, and permissions to TaskFlow.

### Future AuthSphere Features

The following features are planned for the AuthSphere project:

### Authentication
Role-Based Access Control
Organization management
Permissions
Google OAuth
GitHub OAuth
Single Sign-On (SSO)
Multi-Factor Authentication (MFA)

These features are not part of the current TaskFlow demo.

### Purpose

TaskFlow is intentionally kept small.

Its purpose is not to compete with full project-management platforms.

Instead, it provides a realistic application that can be used to
demonstrate how an authentication and authorization platform such as
AuthSphere can secure a third-party application.

### Project Status

### Status: Demo Application

TaskFlow is currently being used as a demonstration application for
the AuthSphere project.

### Author

Satya Brata

GitHub:

https://github.com/Satyabrata11X
