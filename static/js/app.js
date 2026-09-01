/**
 * TaskFlow - Unified Client-Side Application Logic
 * Implements Demo Authentication, State Management, RBAC UI Enforcement,
 * Dynamic Data Fetching, Modals, and Interactive Project Management.
 */

// Global App State
const AppState = {
  currentUser: null,
  projects: [],
  tasks: [],
  users: [],
  activeProjectFilter: 'All',
  activeTaskFilter: 'All',
  projectSearchQuery: '',
  taskSearchQuery: ''
};

// ==========================================================================
// TOAST NOTIFICATIONS
// ==========================================================================
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icon = type === 'success' ? '✓' : '⚠️';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ==========================================================================
// MODAL CONTROLLERS
// ==========================================================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
  }
}

// Close modal when clicking outside modal-dialog
window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('open');
  }
});

// ==========================================================================
// ROLE HELPERS & UI ENFORCEMENT
// ==========================================================================
function getRoleBadgeClass(role) {
  switch ((role || '').toLowerCase()) {
    case 'owner':
      return 'role-owner';
    case 'manager':
      return 'role-manager';
    case 'developer':
      return 'role-developer';
    case 'hr':
      return 'role-hr';
    default:
      return 'role-developer';
  }
}

function getStatusBadgeClass(status) {
  switch ((status || '').toLowerCase()) {
    case 'active':
    case 'in progress':
      return 'status-active';
    case 'completed':
      return 'status-completed';
    case 'planning':
    case 'todo':
      return 'status-planning';
    default:
      return 'status-planning';
  }
}

function hasPermission(permissionName) {
  if (!AppState.currentUser || !AppState.currentUser.permissions) return false;
  return AppState.currentUser.permissions.includes(permissionName);
}

function applyRoleBasedUI() {
  if (!AppState.currentUser) return;
  const role = AppState.currentUser.role;

  // Elements requiring specific permissions
  const projectCreateBtns = document.querySelectorAll('.rbac-project-create');
  projectCreateBtns.forEach(btn => {
    btn.style.display = hasPermission('projects:create') ? 'inline-flex' : 'none';
  });

  const taskCreateBtns = document.querySelectorAll('.rbac-task-create');
  taskCreateBtns.forEach(btn => {
    btn.style.display = hasPermission('tasks:create') ? 'inline-flex' : 'none';
  });
}

// ==========================================================================
// AUTHENTICATION & USER SESSION
// ==========================================================================
async function initCurrentUser() {
  try {
    const res = await fetch('/api/me');
    if (res.status === 401) {
      // If unauthenticated and on a protected app page, redirect to login
      const currentPath = window.location.pathname;
      const publicPaths = ['/', '/index.html', '/login', '/login.html'];
      if (!publicPaths.includes(currentPath)) {
        window.location.href = '/login.html';
      }
      return null;
    }

    if (!res.ok) {
      throw new Error('Failed to fetch user state');
    }

    const userData = await res.json();
    AppState.currentUser = userData;

    // Update UI headers and sidebars if elements exist
    updateUserInterface(userData);
    applyRoleBasedUI();

    return userData;
  } catch (err) {
    console.error('Error in initCurrentUser:', err);
    return null;
  }
}

function updateUserInterface(user) {
  // Update sidebar profile
  const userNameElem = document.getElementById('sidebar-user-name');
  const userRoleElem = document.getElementById('sidebar-user-role');
  const userAvatarElem = document.getElementById('sidebar-user-avatar');
  const orgNameElem = document.getElementById('sidebar-org-name');

  if (userNameElem) userNameElem.textContent = user.name;
  if (userRoleElem) {
    userRoleElem.textContent = user.role;
    userRoleElem.className = `role-badge ${getRoleBadgeClass(user.role)}`;
  }
  if (userAvatarElem) {
    userAvatarElem.textContent = (user.name || 'U').charAt(0).toUpperCase();
  }
  if (orgNameElem) orgNameElem.textContent = user.organization;

  // Update top navbar greetings if present
  const greetingName = document.getElementById('greeting-user-name');
  const greetingRole = document.getElementById('greeting-user-role');
  const greetingOrg = document.getElementById('greeting-user-org');

  if (greetingName) greetingName.textContent = user.name;
  if (greetingRole) {
    greetingRole.textContent = user.role;
    greetingRole.className = `role-badge ${getRoleBadgeClass(user.role)}`;
  }
  if (greetingOrg) greetingOrg.textContent = user.organization;
}

async function loginAsDemoUser(userId) {
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });

    const data = await res.json();
    if (res.ok) {
      showToast(`Logged in as ${data.user.name}`, 'success');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 400);
    } else {
      showToast(data.error || 'Login failed', 'error');
    }
  } catch (err) {
    showToast('Network error during login', 'error');
    console.error(err);
  }
}

async function logout() {
  try {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login.html';
  } catch (err) {
    window.location.href = '/login.html';
  }
}

// ==========================================================================
// DASHBOARD VIEW
// ==========================================================================
async function loadDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    if (!res.ok) {
      if (res.status === 401) window.location.href = '/login.html';
      throw new Error('Failed to fetch dashboard metrics');
    }

    const data = await res.json();

    // Populate stat counters
    const totalProjectsElem = document.getElementById('stat-total-projects');
    const activeTasksElem = document.getElementById('stat-active-tasks');
    const teamMembersElem = document.getElementById('stat-team-members');
    const completedPctElem = document.getElementById('stat-completed-pct');

    if (totalProjectsElem) totalProjectsElem.textContent = data.total_projects;
    if (activeTasksElem) activeTasksElem.textContent = data.active_tasks;
    if (teamMembersElem) teamMembersElem.textContent = data.team_members;
    if (completedPctElem) completedPctElem.textContent = `${data.completed_percentage}%`;

    // Render Recent Projects
    renderDashboardRecentProjects(data.recent_projects || []);

    // Render Recent Activities
    renderDashboardActivities(data.recent_activities || []);
  } catch (err) {
    console.error('Error loading dashboard:', err);
  }
}

function renderDashboardRecentProjects(projects) {
  const container = document.getElementById('dashboard-recent-projects');
  if (!container) return;

  if (projects.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding: 24px;">
        <p class="empty-state-desc">No projects found. Create your first project to get started!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = projects.map(p => `
    <div class="project-item-compact">
      <div class="project-item-header">
        <span class="project-item-name">${escapeHTML(p.name)}</span>
        <span class="status-badge ${getStatusBadgeClass(p.status)}">${p.status}</span>
      </div>
      <div style="font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between;">
        <span>Progress: ${p.progress}%</span>
        <span>${p.task_count || 0} tasks • ${p.member_count || 0} members</span>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width: ${p.progress}%;"></div>
      </div>
    </div>
  `).join('');
}

function renderDashboardActivities(activities) {
  const container = document.getElementById('dashboard-recent-activities');
  if (!container) return;

  if (activities.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding: 24px;">
        <p class="empty-state-desc">No recent activity recorded yet.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = activities.map(a => `
    <div class="activity-item">
      <div class="activity-dot"></div>
      <div class="activity-content">
        <div>
          <span class="activity-actor">${escapeHTML(a.user_name)}</span>
          <span class="role-badge ${getRoleBadgeClass(a.user_role)}" style="font-size: 0.68rem; padding: 0 6px; margin: 0 4px;">${a.user_role}</span>
          ${escapeHTML(a.action)}
        </div>
        <div class="activity-time">${formatTime(a.created_at)}</div>
      </div>
    </div>
  `).join('');
}

// ==========================================================================
// PROJECTS VIEW & MANAGEMENT
// ==========================================================================
async function loadProjects() {
  try {
    const res = await fetch('/api/projects');
    if (!res.ok) {
      if (res.status === 401) window.location.href = '/login.html';
      throw new Error('Failed to fetch projects');
    }

    AppState.projects = await res.json();
    filterAndRenderProjects();
  } catch (err) {
    console.error('Error loading projects:', err);
    showToast('Failed to load projects', 'error');
  }
}

function filterAndRenderProjects() {
  const container = document.getElementById('projects-grid-container');
  if (!container) return;

  let filtered = AppState.projects;

  // Status Filter
  if (AppState.activeProjectFilter !== 'All') {
    filtered = filtered.filter(p => p.status.toLowerCase() === AppState.activeProjectFilter.toLowerCase());
  }

  // Search Filter
  if (AppState.projectSearchQuery.trim()) {
    const query = AppState.projectSearchQuery.toLowerCase();
    filtered = filtered.filter(p => 
      p.name.toLowerCase().includes(query) || 
      (p.description && p.description.toLowerCase().includes(query))
    );
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <div class="empty-state-icon">📁</div>
        <h4 class="empty-state-title">No Projects Found</h4>
        <p class="empty-state-desc">No projects match the current filter or search criteria.</p>
      </div>
    `;
    return;
  }

  const canEdit = hasPermission('projects:edit');
  const canDelete = hasPermission('projects:delete');

  container.innerHTML = filtered.map(p => {
    const memberAvatars = (p.members || []).map(m => 
      `<div class="project-member-avatar" title="${escapeHTML(m.name)} (${m.role})">${(m.name || 'U').charAt(0).toUpperCase()}</div>`
    ).join('');

    return `
      <div class="project-card" id="project-card-${p.id}">
        <div>
          <div class="project-card-header">
            <h3 class="project-card-title">${escapeHTML(p.name)}</h3>
            <span class="status-badge ${getStatusBadgeClass(p.status)}">${p.status}</span>
          </div>
          <p class="project-card-desc">${escapeHTML(p.description || 'No description provided.')}</p>
          
          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">
              <span>Progress</span>
              <span>${p.progress}%</span>
            </div>
            <div class="progress-bar-container">
              <div class="progress-bar-fill" style="width: ${p.progress}%;"></div>
            </div>
          </div>
          
          <div style="font-size: 0.78rem; color: var(--text-muted); display: flex; gap: 12px;">
            <span>Tasks: <strong>${p.completed_tasks || 0}/${p.total_tasks || 0}</strong> completed</span>
          </div>
        </div>

        <div class="project-card-footer">
          <div class="project-members-group">
            ${memberAvatars || '<span style="font-size: 0.78rem; color: var(--text-muted);">No members</span>'}
          </div>
          <div style="display: flex; gap: 6px;">
            ${canEdit ? `<button class="btn btn-secondary btn-sm" onclick="openEditProjectModal(${p.id})">Edit</button>` : ''}
            ${canDelete ? `<button class="btn btn-danger btn-sm" onclick="deleteProject(${p.id})">Delete</button>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function openCreateProjectModal() {
  document.getElementById('project-form').reset();
  document.getElementById('project-modal-title').textContent = 'Create New Project';
  document.getElementById('project-id-input').value = '';

  await populateProjectMemberCheckboxes();
  openModal('project-modal');
}

async function openEditProjectModal(projectId) {
  const project = AppState.projects.find(p => p.id === projectId);
  if (!project) return;

  document.getElementById('project-modal-title').textContent = 'Edit Project';
  document.getElementById('project-id-input').value = project.id;
  document.getElementById('project-name-input').value = project.name;
  document.getElementById('project-desc-input').value = project.description || '';
  document.getElementById('project-status-select').value = project.status;
  document.getElementById('project-progress-input').value = project.progress;

  const currentMemberIds = (project.members || []).map(m => m.id);
  await populateProjectMemberCheckboxes(currentMemberIds);

  openModal('project-modal');
}

async function populateProjectMemberCheckboxes(selectedIds = []) {
  const container = document.getElementById('project-members-container');
  if (!container) return;

  if (AppState.users.length === 0) {
    try {
      const res = await fetch('/api/users');
      if (res.ok) AppState.users = await res.json();
    } catch (e) {
      console.error(e);
    }
  }

  container.innerHTML = AppState.users.map(u => {
    const isChecked = selectedIds.includes(u.id) ? 'checked' : '';
    return `
      <label style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; cursor: pointer; padding: 4px 0;">
        <input type="checkbox" name="project_members" value="${u.id}" ${isChecked}>
        <span>${escapeHTML(u.name)}</span>
        <span class="role-badge ${getRoleBadgeClass(u.role)}" style="font-size: 0.7rem;">${u.role}</span>
      </label>
    `;
  }).join('');
}

async function handleProjectFormSubmit(e) {
  e.preventDefault();

  const projectId = document.getElementById('project-id-input').value;
  const name = document.getElementById('project-name-input').value.trim();
  const description = document.getElementById('project-desc-input').value.trim();
  const status = document.getElementById('project-status-select').value;
  const progress = parseInt(document.getElementById('project-progress-input').value) || 0;

  const memberCheckboxes = document.querySelectorAll('input[name="project_members"]:checked');
  const member_ids = Array.from(memberCheckboxes).map(cb => parseInt(cb.value));

  const payload = { name, description, status, progress, member_ids };

  try {
    let res;
    if (projectId) {
      res = await fetch(`/api/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }

    const data = await res.json();
    if (res.ok) {
      closeModal('project-modal');
      showToast(projectId ? 'Project updated successfully' : 'Project created successfully', 'success');
      await loadProjects();
    } else {
      showToast(data.error || 'Failed to save project', 'error');
    }
  } catch (err) {
    showToast('Network error saving project', 'error');
    console.error(err);
  }
}

async function deleteProject(projectId) {
  if (!confirm('Are you sure you want to delete this project? All associated tasks will be removed.')) {
    return;
  }

  try {
    const res = await fetch(`/api/projects/${projectId}`, {
      method: 'DELETE'
    });

    const data = await res.json();
    if (res.ok) {
      showToast('Project deleted successfully', 'success');
      await loadProjects();
    } else {
      showToast(data.error || 'Forbidden: Insufficient permissions', 'error');
    }
  } catch (err) {
    showToast('Network error deleting project', 'error');
    console.error(err);
  }
}

// ==========================================================================
// TASKS VIEW & MANAGEMENT
// ==========================================================================
async function loadTasks() {
  try {
    const [tasksRes, projectsRes, usersRes] = await Promise.all([
      fetch('/api/tasks'),
      fetch('/api/projects'),
      fetch('/api/users')
    ]);

    if (!tasksRes.ok) {
      if (tasksRes.status === 401) window.location.href = '/login.html';
      throw new Error('Failed to fetch tasks');
    }

    AppState.tasks = await tasksRes.json();
    if (projectsRes.ok) AppState.projects = await projectsRes.json();
    if (usersRes.ok) AppState.users = await usersRes.json();

    filterAndRenderTasks();
  } catch (err) {
    console.error('Error loading tasks:', err);
    showToast('Failed to load tasks', 'error');
  }
}

function filterAndRenderTasks() {
  const container = document.getElementById('tasks-container');
  if (!container) return;

  let filtered = AppState.tasks;

  // Status Filter
  if (AppState.activeTaskFilter !== 'All') {
    filtered = filtered.filter(t => t.status.toLowerCase() === AppState.activeTaskFilter.toLowerCase());
  }

  // Search Filter
  if (AppState.taskSearchQuery.trim()) {
    const query = AppState.taskSearchQuery.toLowerCase();
    filtered = filtered.filter(t => 
      t.title.toLowerCase().includes(query) || 
      (t.description && t.description.toLowerCase().includes(query)) ||
      (t.project_name && t.project_name.toLowerCase().includes(query))
    );
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <h4 class="empty-state-title">No Tasks Found</h4>
        <p class="empty-state-desc">No tasks match your current filter. Create a new task to get started!</p>
      </div>
    `;
    return;
  }

  const userRole = AppState.currentUser ? AppState.currentUser.role : '';
  const canEditTask = hasPermission('tasks:edit');
  const canDeleteTask = hasPermission('tasks:delete');
  const canUpdateStatus = hasPermission('tasks:update_status') || canEditTask;

  container.innerHTML = filtered.map(t => {
    const isCompleted = t.status === 'Completed';

    return `
      <div class="task-card" id="task-card-${t.id}">
        <div class="task-main-info">
          <div>
            ${canUpdateStatus ? `
              <select class="task-status-selector" onchange="quickUpdateTaskStatus(${t.id}, this.value)" style="${isCompleted ? 'background: #ecfdf5; color: #047857; border-color: #a7f3d0;' : ''}">
                <option value="Todo" ${t.status === 'Todo' ? 'selected' : ''}>Todo</option>
                <option value="In Progress" ${t.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                <option value="Completed" ${t.status === 'Completed' ? 'selected' : ''}>Completed</option>
              </select>
            ` : `
              <span class="status-badge ${getStatusBadgeClass(t.status)}">${t.status}</span>
            `}
          </div>
          <div class="task-details">
            <h4 class="task-title" style="${isCompleted ? 'text-decoration: line-through; color: var(--text-muted);' : ''}">${escapeHTML(t.title)}</h4>
            ${t.description ? `<p class="task-desc">${escapeHTML(t.description)}</p>` : ''}
            <div class="task-meta">
              <span class="task-project-pill">📁 ${escapeHTML(t.project_name || 'General')}</span>
              <span class="task-assignee">
                👤 ${t.assignee_name ? `${escapeHTML(t.assignee_name)} <span class="role-badge ${getRoleBadgeClass(t.assignee_role)}" style="font-size: 0.65rem;">${t.assignee_role}</span>` : 'Unassigned'}
              </span>
            </div>
          </div>
        </div>

        <div class="task-actions">
          ${canEditTask ? `<button class="btn btn-secondary btn-sm" onclick="openEditTaskModal(${t.id})">Edit</button>` : ''}
          ${canDeleteTask ? `<button class="btn btn-danger btn-sm" onclick="deleteTask(${t.id})">Delete</button>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

async function quickUpdateTaskStatus(taskId, newStatus) {
  try {
    const res = await fetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });

    const data = await res.json();
    if (res.ok) {
      showToast(`Task status changed to ${newStatus}`, 'success');
      await loadTasks();
    } else {
      showToast(data.error || 'Failed to update task status', 'error');
    }
  } catch (err) {
    showToast('Network error updating task', 'error');
    console.error(err);
  }
}

async function openCreateTaskModal() {
  document.getElementById('task-form').reset();
  document.getElementById('task-modal-title').textContent = 'Create New Task';
  document.getElementById('task-id-input').value = '';

  populateTaskDropdowns();
  openModal('task-modal');
}

async function openEditTaskModal(taskId) {
  const task = AppState.tasks.find(t => t.id === taskId);
  if (!task) return;

  document.getElementById('task-modal-title').textContent = 'Edit Task';
  document.getElementById('task-id-input').value = task.id;
  document.getElementById('task-title-input').value = task.title;
  document.getElementById('task-desc-input').value = task.description || '';
  document.getElementById('task-status-input').value = task.status;

  populateTaskDropdowns(task.project_id, task.assigned_to);
  openModal('task-modal');
}

function populateTaskDropdowns(selectedProjectId = null, selectedUserId = null) {
  const projectSelect = document.getElementById('task-project-select');
  const assigneeSelect = document.getElementById('task-assignee-select');

  if (projectSelect) {
    projectSelect.innerHTML = AppState.projects.map(p => `
      <option value="${p.id}" ${p.id == selectedProjectId ? 'selected' : ''}>${escapeHTML(p.name)}</option>
    `).join('');
  }

  if (assigneeSelect) {
    assigneeSelect.innerHTML = `
      <option value="">-- Unassigned --</option>
      ${AppState.users.map(u => `
        <option value="${u.id}" ${u.id == selectedUserId ? 'selected' : ''}>${escapeHTML(u.name)} (${u.role})</option>
      `).join('')}
    `;
  }
}

async function handleTaskFormSubmit(e) {
  e.preventDefault();

  const taskId = document.getElementById('task-id-input').value;
  const title = document.getElementById('task-title-input').value.trim();
  const description = document.getElementById('task-desc-input').value.trim();
  const status = document.getElementById('task-status-input').value;
  const project_id = parseInt(document.getElementById('task-project-select').value);
  const assigned_to_val = document.getElementById('task-assignee-select').value;
  const assigned_to = assigned_to_val ? parseInt(assigned_to_val) : null;

  const payload = { title, description, status, project_id, assigned_to };

  try {
    let res;
    if (taskId) {
      res = await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }

    const data = await res.json();
    if (res.ok) {
      closeModal('task-modal');
      showToast(taskId ? 'Task updated successfully' : 'Task created successfully', 'success');
      await loadTasks();
    } else {
      showToast(data.error || 'Failed to save task', 'error');
    }
  } catch (err) {
    showToast('Network error saving task', 'error');
    console.error(err);
  }
}

async function deleteTask(taskId) {
  if (!confirm('Are you sure you want to delete this task?')) return;

  try {
    const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast('Task deleted successfully', 'success');
      await loadTasks();
    } else {
      showToast(data.error || 'Forbidden: Insufficient permissions', 'error');
    }
  } catch (err) {
    showToast('Network error deleting task', 'error');
    console.error(err);
  }
}

// ==========================================================================
// TEAM VIEW
// ==========================================================================
async function loadTeam() {
  try {
    const res = await fetch('/api/users');
    if (!res.ok) {
      if (res.status === 401) window.location.href = '/login.html';
      throw new Error('Failed to fetch team members');
    }

    const users = await res.json();
    AppState.users = users;

    const container = document.getElementById('team-grid-container');
    if (!container) return;

    container.innerHTML = users.map(u => `
      <div class="team-card">
        <div class="team-avatar-large">${(u.name || 'U').charAt(0).toUpperCase()}</div>
        <h3 class="team-name">${escapeHTML(u.name)}</h3>
        <p class="team-email">${escapeHTML(u.email)}</p>
        <span class="role-badge ${getRoleBadgeClass(u.role)}">${u.role}</span>
        <div class="team-org">Organization: <strong>${escapeHTML(u.organization)}</strong></div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading team:', err);
    showToast('Failed to load team members', 'error');
  }
}

// ==========================================================================
// UTILITY FUNCTIONS
// ==========================================================================
function escapeHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp + 'Z');
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec < 60) return 'just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ==========================================================================
// DOM INITIALIZER
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Initialize Current User
  await initCurrentUser();

  // 2. Page Specific Initializations based on DOM elements present
  const isDashboardPage = document.getElementById('stat-total-projects') !== null;
  const isProjectsPage = document.getElementById('projects-grid-container') !== null;
  const isTasksPage = document.getElementById('tasks-container') !== null;
  const isTeamPage = document.getElementById('team-grid-container') !== null;

  if (isDashboardPage) {
    await loadDashboard();
  }

  if (isProjectsPage) {
    // Project Search Listener
    const projectSearchInput = document.getElementById('project-search-input');
    if (projectSearchInput) {
      projectSearchInput.addEventListener('input', (e) => {
        AppState.projectSearchQuery = e.target.value;
        filterAndRenderProjects();
      });
    }

    // Project Filter Tabs
    const filterTabs = document.querySelectorAll('.project-filter-tab');
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        AppState.activeProjectFilter = tab.dataset.filter;
        filterAndRenderProjects();
      });
    });

    // Project Form Submit Listener
    const projectForm = document.getElementById('project-form');
    if (projectForm) {
      projectForm.addEventListener('submit', handleProjectFormSubmit);
    }

    await loadProjects();
  }

  if (isTasksPage) {
    // Task Search Listener
    const taskSearchInput = document.getElementById('task-search-input');
    if (taskSearchInput) {
      taskSearchInput.addEventListener('input', (e) => {
        AppState.taskSearchQuery = e.target.value;
        filterAndRenderTasks();
      });
    }

    // Task Filter Tabs
    const taskTabs = document.querySelectorAll('.task-filter-tab');
    taskTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        taskTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        AppState.activeTaskFilter = tab.dataset.filter;
        filterAndRenderTasks();
      });
    });

    // Task Form Submit Listener
    const taskForm = document.getElementById('task-form');
    if (taskForm) {
      taskForm.addEventListener('submit', handleTaskFormSubmit);
    }

    await loadTasks();
  }

  if (isTeamPage) {
    await loadTeam();
  }
});
