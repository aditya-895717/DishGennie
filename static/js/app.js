/**
 * DishGennie — Core Application JavaScript
 * API Client, Auth Manager, Toast System, Utilities
 */

const DG = {
    // ─── API Client ───
    API_BASE: '/api/v1',

    getToken() {
        return localStorage.getItem('dg_access');
    },

    getUser() {
        try { return JSON.parse(localStorage.getItem('dg_user')); }
        catch { return null; }
    },

    getCSRFToken() {
        // Get CSRF token from cookie (most reliable method)
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        // Fallback: get from meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;
        // Fallback: get from hidden input
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        return '';
    },

    async api(endpoint, options = {}) {
        const url = `${this.API_BASE}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const token = this.getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const csrfToken = this.getCSRFToken();
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;

        try {
            const res = await fetch(url, { ...options, headers });

            if (res.status === 401) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    headers['Authorization'] = `Bearer ${this.getToken()}`;
                    return fetch(url, { ...options, headers }).then(r => r.json());
                }
                // If refresh fails, redirect to login
                this.clearAuth();
                window.location.href = '/accounts/login/';
                return null;
            }

            return await res.json();
        } catch (err) {
            console.error('API Error:', err);
            this.toast('Error', 'Network error. Please try again.', 'error');
            return null;
        }
    },

    async refreshToken() {
        const refresh = localStorage.getItem('dg_refresh');
        if (!refresh) return false;
        try {
            const res = await fetch(`${this.API_BASE}/accounts/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh }),
            });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('dg_access', data.access);
                return true;
            }
        } catch {}
        return false;
    },

    clearAuth() {
        localStorage.removeItem('dg_access');
        localStorage.removeItem('dg_refresh');
        localStorage.removeItem('dg_user');
    },

    // ─── Logout (POST-based) ───
    logout() {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/accounts/logout/';
        const csrf = document.createElement('input');
        csrf.type = 'hidden';
        csrf.name = 'csrfmiddlewaretoken';
        csrf.value = this.getCSRFToken();
        form.appendChild(csrf);
        document.body.appendChild(form);
        this.clearAuth();
        form.submit();
    },

    // ─── Toast Notifications ───
    toast(title, message = '', type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const icons = {
            success: 'bi-check-circle-fill text-success',
            error: 'bi-exclamation-circle-fill text-danger',
            warning: 'bi-exclamation-triangle-fill text-warning',
            info: 'bi-info-circle-fill text-primary',
        };

        const toast = document.createElement('div');
        toast.className = `dg-toast ${type}`;
        toast.innerHTML = `
            <i class="dg-toast-icon bi ${icons[type] || icons.info}"></i>
            <div class="dg-toast-content">
                <div class="dg-toast-title">${title}</div>
                ${message ? `<div class="dg-toast-message">${message}</div>` : ''}
            </div>
            <button onclick="this.parentElement.classList.add('toast-exit');setTimeout(()=>this.parentElement.remove(),300)" style="background:none;border:none;color:var(--gray-400);cursor:pointer;font-size:1.1rem;padding:0 4px"><i class="bi bi-x"></i></button>
        `;
        container.appendChild(toast);

        // Auto-dismiss with slide-out animation
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    },

    // ─── Confirmation Modal ───
    confirm(title, message, onConfirm, options = {}) {
        const modal = document.createElement('div');
        modal.className = 'dg-modal-overlay';
        modal.innerHTML = `
            <div class="dg-confirm-modal">
                <div class="dg-confirm-icon ${options.type || 'warning'}">
                    <i class="bi bi-${options.icon || 'exclamation-triangle'}"></i>
                </div>
                <h4 class="dg-confirm-title">${title}</h4>
                <p class="dg-confirm-text">${message}</p>
                <div class="dg-confirm-actions">
                    <button class="btn-premium-outline dg-confirm-cancel">Cancel</button>
                    <button class="btn-premium dg-confirm-ok" style="${options.danger ? 'background:linear-gradient(135deg,#ef4444,#dc2626)' : ''}">
                        ${options.confirmText || 'Confirm'}
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        requestAnimationFrame(() => modal.classList.add('show'));

        modal.querySelector('.dg-confirm-cancel').onclick = () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        };
        modal.querySelector('.dg-confirm-ok').onclick = () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
            if (onConfirm) onConfirm();
        };
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
            }
        });
    },

    // ─── Utilities ───
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency', currency: 'INR', maximumFractionDigits: 0,
        }).format(amount);
    },

    formatDate(dateStr) {
        return new Date(dateStr).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric',
        });
    },

    formatTime(dateStr) {
        return new Date(dateStr).toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit',
        });
    },

    debounce(func, wait = 300) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    asList(data) {
        return Array.isArray(data) ? data : (data?.results || []);
    },

    setCountBadge(selector, count) {
        const value = Number(count || 0);
        document.querySelectorAll(selector).forEach(badge => {
            badge.textContent = value > 99 ? '99+' : String(value);
            badge.hidden = value <= 0;
        });
    },

    async updateNotificationCount() {
        if (!document.querySelector('meta[name="user-id"]')) return;
        const data = await this.api('/notifications/summary/');
        if (!data || data.error) return;
        this.setCountBadge('[data-notification-count]', data.unread_count);
    },

    // ─── Notification Dropdown ───
    notifPanelOpen: false,

    async toggleNotificationPanel() {
        let panel = document.getElementById('notifPanel');
        if (panel) {
            this.notifPanelOpen = !this.notifPanelOpen;
            panel.classList.toggle('show', this.notifPanelOpen);
            const bd = document.getElementById('notifBackdrop');
            if (bd) bd.classList.toggle('show', this.notifPanelOpen);
            if (this.notifPanelOpen) this.loadNotifications();
            return;
        }
        // Create backdrop for mobile
        let backdrop = document.createElement('div');
        backdrop.id = 'notifBackdrop';
        backdrop.className = 'notif-backdrop';
        document.body.appendChild(backdrop);
        backdrop.addEventListener('click', () => {
            this.notifPanelOpen = false;
            panel.classList.remove('show');
            backdrop.classList.remove('show');
        });

        panel = document.createElement('div');
        panel.id = 'notifPanel';
        panel.className = 'notif-panel';
        panel.innerHTML = `
            <div class="notif-panel-header">
                <h4><i class="bi bi-bell"></i> Notifications</h4>
                <div class="d-flex align-items-center gap-2">
                    <button class="notif-mark-read" id="markAllRead"><i class="bi bi-check-all"></i> Mark all read</button>
                    <button class="notif-close" id="notifClose"><i class="bi bi-x-lg"></i></button>
                </div>
            </div>
            <div class="notif-panel-body" id="notifList">
                <div class="notif-loading"><div class="spinner-border spinner-border-sm"></div> Loading...</div>
            </div>
        `;
        const btn = document.getElementById('notifBtn');
        document.body.appendChild(panel);

        document.addEventListener('click', (e) => {
            if (this.notifPanelOpen && !panel.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
                this.notifPanelOpen = false;
                panel.classList.remove('show');
                backdrop.classList.remove('show');
            }
        });

        document.getElementById('markAllRead').addEventListener('click', async () => {
            await this.markNotificationsRead();
        });

        document.getElementById('notifClose').addEventListener('click', () => {
            this.notifPanelOpen = false;
            panel.classList.remove('show');
            backdrop.classList.remove('show');
        });

        this.notifPanelOpen = true;
        panel.classList.add('show');
        backdrop.classList.add('show');
        this.loadNotifications();
    },

    async loadNotifications() {
        const data = await this.api('/notifications/');
        const list = this.asList(data);
        const container = document.getElementById('notifList');
        if (!container) return;

        if (list.length === 0) {
            container.innerHTML = `
                <div class="notif-empty">
                    <i class="bi bi-bell-slash"></i>
                    <p>No notifications yet</p>
                </div>`;
            return;
        }

        const icons = {
            booking: 'bi-calendar-check text-primary',
            payment: 'bi-credit-card text-success',
            system: 'bi-gear text-secondary',
            promo: 'bi-gift text-warning',
            alert: 'bi-exclamation-triangle text-danger',
        };

        container.innerHTML = list.slice(0, 20).map(n => {
            const icon = icons[n.notif_type] || icons.system;
            const time = this.timeAgo(n.created_at);
            const unread = !n.is_read ? 'notif-unread' : '';
            return `<a href="${n.action_url || '#'}" class="notif-item ${unread}">
                <div class="notif-item-icon"><i class="bi ${icon}"></i></div>
                <div class="notif-item-content">
                    <div class="notif-item-title">${n.title}</div>
                    <div class="notif-item-msg">${n.message}</div>
                    <div class="notif-item-time"><i class="bi bi-clock"></i> ${time}</div>
                </div>
                ${!n.is_read ? '<div class="notif-dot"></div>' : ''}
            </a>`;
        }).join('');
    },

    timeAgo(dateStr) {
        const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
        return new Date(dateStr).toLocaleDateString('en-IN', {day:'numeric',month:'short'});
    },

    async markNotificationsRead() {
        const data = await this.api('/notifications/read/', { method: 'POST', body: JSON.stringify({}) });
        if (data && !data.error) {
            this.setCountBadge('[data-notification-count]', 0);
            document.querySelectorAll('.notif-item.notif-unread').forEach(el => {
                el.classList.remove('notif-unread');
                const dot = el.querySelector('.notif-dot');
                if (dot) dot.remove();
            });
            this.toast('Done', 'All notifications marked as read.', 'success');
        }
    },

    async updateRoleBadges() {
        const role = document.querySelector('meta[name="user-role"]')?.content || document.querySelector('.dg-app')?.dataset.theme;
        if (role === 'maid') {
            const requests = this.asList(await this.api('/bookings/maid/requests/'));
            this.setCountBadge('#reqBadge', requests.length);
        }
        if (role === 'admin') {
            const pending = this.asList(await this.api('/accounts/admin/maids/?status=pending'));
            this.setCountBadge('#verificationBadge', pending.length);
        }
    },

    // ─── Animated Counters ───
    animateCounter(element, target, duration = 1500) {
        const start = 0;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(start + (target - start) * eased);

            if (typeof target === 'number') {
                element.textContent = current.toLocaleString('en-IN');
            }

            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    },

    // ─── Initialize ───
    init() {
        // Page load animation
        document.body.classList.add('dg-page-loaded');

        // Store JWT tokens from server-rendered context (if present)
        const tokenMeta = document.querySelector('meta[name="jwt-access"]');
        if (tokenMeta && tokenMeta.content) {
            localStorage.setItem('dg_access', tokenMeta.content);
        }
        const refreshMeta = document.querySelector('meta[name="jwt-refresh"]');
        if (refreshMeta && refreshMeta.content) {
            localStorage.setItem('dg_refresh', refreshMeta.content);
        }

        // Animate elements on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.animate-fade-in-up').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            observer.observe(el);
        });

        // Active nav link highlight
        const currentPath = window.location.pathname;
        document.querySelectorAll('.dg-nav-link').forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });

        // Smooth page transitions for internal links
        document.querySelectorAll('a[href^="/"]').forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href && !href.startsWith('#') && !this.hasAttribute('download') && !e.ctrlKey && !e.metaKey) {
                    document.body.classList.add('dg-page-exit');
                }
            });
        });

        this.updateNotificationCount();
        this.updateRoleBadges();
        document.getElementById('notifBtn')?.addEventListener('click', (e) => { e.stopPropagation(); this.toggleNotificationPanel(); });
    }
};

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => DG.init());
