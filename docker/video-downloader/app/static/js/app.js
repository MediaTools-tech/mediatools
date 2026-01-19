/**
 * Video Downloader Docker - Frontend JavaScript
 * WebSocket connection, real-time updates, and UI interactions
 */

// =============================================
// WebSocket Connection
// =============================================

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.listeners = new Map();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.emit('connected');
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.emit('disconnected');
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }

    handleMessage(message) {
        const { type, data } = message;

        switch (type) {
            case 'initial_state':
                this.emit('initial_state', data);
                break;
            case 'status_update':
                this.emit('status_update', data);
                break;
            case 'queue_update':
                this.emit('queue_update', data);
                break;
            case 'download_complete':
                this.emit('download_complete', data);
                break;
            case 'download_failed':
                this.emit('download_failed', data);
                break;
            case 'ping':
                this.send({ type: 'pong' });
                break;
            default:
                console.log('Received WebSocket message:', type, data);
        }
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    emit(event, data) {
        if (event !== 'ping' && event !== 'pong') {
            console.log(`WebSocket EMIT: ${event}`, data);
        }
        const callbacks = this.listeners.get(event) || [];
        callbacks.forEach(callback => callback(data));
    }
}


// =============================================
// App State
// =============================================

const state = {
    status: 'idle',
    statusMessage: 'Ready',
    progress: {
        percentage: 0,
        speed: '',
        eta: '',
        filename: ''
    },
    queue: [],
    queueCount: 0,
    failedCount: 0,
    settings: {}, // Store settings from backend
    downloadType: 'video' // Track current download type
};


// =============================================
// DOM Elements
// =============================================

const elements = {};

function cacheElements() {
    elements.urlInput = document.getElementById('url-input');
    elements.btnVideo = document.getElementById('btn-video');
    elements.btnAudio = document.getElementById('btn-audio');
    elements.btnDownloads = document.getElementById('btn-downloads');
    elements.btnDocs = document.getElementById('btn-docs');
    elements.btnPlayLatest = document.getElementById('btn-play-latest');
    elements.btnExit = document.getElementById('btn-exit');
    elements.btnCancel = document.getElementById('btn-cancel');
    elements.btnPause = document.getElementById('btn-pause');
    elements.btnThemeToggle = document.getElementById('theme-toggle');
    elements.btnClearQueue = document.getElementById('btn-clear-queue');
    elements.statusIndicator = document.getElementById('status-indicator');
    elements.statusText = document.getElementById('status-text');
    elements.progressContainer = document.getElementById('progress-container');
    elements.progressFill = document.getElementById('progress-fill');

    // Session Modal
    elements.sessionModal = document.getElementById('session-modal');
    elements.sessionQueueCount = document.getElementById('session-queue-count');
    elements.sessionFailedCount = document.getElementById('session-failed-count');
    elements.btnSessionDelete = document.getElementById('session-btn-delete');
    elements.btnSessionIgnore = document.getElementById('session-btn-ignore');
    elements.btnSessionContinue = document.getElementById('session-btn-continue');
    elements.btnSessionShow = document.getElementById('session-btn-show');
    elements.sessionDetails = document.getElementById('session-details');
    elements.sessionUrlList = document.getElementById('session-url-list');
    elements.progressPercent = document.getElementById('progress-percent');
    elements.progressSpeed = document.getElementById('progress-speed');
    elements.progressEta = document.getElementById('progress-eta');
    elements.progressFilename = document.getElementById('progress-filename');
    elements.queueCount = document.getElementById('queue-count');
    elements.queueList = document.getElementById('queue-list');
}


// =============================================
// UI Updates
// =============================================

function updateStatus(status, message) {
    state.status = status;
    state.statusMessage = message || status;

    if (elements.statusIndicator) {
        // Remove all status classes
        elements.statusIndicator.classList.remove('idle', 'downloading', 'error', 'completed');

        // Add appropriate class
        if (status === 'idle' || status === 'completed') {
            elements.statusIndicator.classList.add('idle');
        } else if (status === 'error' || status === 'cancelled') {
            elements.statusIndicator.classList.add('error');
        } else if (status === 'paused') {
            elements.statusIndicator.classList.add('idle'); // Or a custom 'paused' class if you have one
        } else {
            elements.statusIndicator.classList.add('downloading');
        }
    }

    if (elements.statusText) {
        elements.statusText.textContent = state.statusMessage;
    }

    // Show/hide controls based on status
    const isDownloading = ['downloading', 'fetching_metadata', 'analyzing',
        'converting', 'merging', 'post_processing'].includes(status);

    if (elements.btnCancel) {
        elements.btnCancel.classList.toggle('hidden', !isDownloading);
    }
    if (elements.btnPause) {
        // Check if pause is supported for this format/type
        // For video, only support pause if it's the high-quality merge format
        const isVideo = state.downloadType === 'video';
        const isMkvFormat = state.settings?.stream_and_merge_format === 'bestvideo+bestaudio/best-mkv';
        const isPauseSupported = !isVideo || isMkvFormat;

        const canPause = isPauseSupported && (isDownloading || status === 'paused');
        elements.btnPause.classList.toggle('hidden', !canPause);

        // Toggle button text/icon
        if (status === 'paused') {
            elements.btnPause.innerHTML = '<span class="icon">▶</span> Resume';
            elements.btnPause.classList.add('btn-success');
        } else {
            elements.btnPause.innerHTML = '<span class="icon">⏸</span> Pause';
            elements.btnPause.classList.remove('btn-success');
        }
    }

    // Keep progress container visible (persistent)
    if (elements.progressContainer) {
        elements.progressContainer.classList.remove('hidden');
    }

    // Reset progress to 0 if we just completed or are idle
    if (status === 'completed' || status === 'idle' || status === 'cancelled') {
        updateProgress({
            percentage: 0,
            speed: '',
            eta: '',
            filename: ''
        });
    }
}

function updateProgress(progress) {
    if (!progress) return;

    // Merge new progress into state
    state.progress = { ...state.progress, ...progress };

    console.log('Updating progress UI with state:', state.progress);

    // Update UI from state
    if (elements.progressFill) {
        elements.progressFill.style.width = `${state.progress.percentage || 0}%`;
    }
    if (elements.progressPercent) {
        elements.progressPercent.textContent = `${Math.round(state.progress.percentage || 0)}%`;
    }
    if (elements.progressSpeed) {
        elements.progressSpeed.textContent = state.progress.speed || '';
    }
    if (elements.progressEta) {
        elements.progressEta.textContent = state.progress.eta ? `ETA: ${state.progress.eta}` : '';
    }
    if (elements.progressFilename) {
        elements.progressFilename.textContent = state.progress.filename || '';
    }
}

function updateQueue(queueData) {
    state.queue = queueData.queued_urls || [];
    state.queueCount = queueData.queue_count || 0;
    state.failedCount = queueData.failed_count || 0;

    if (elements.queueCount) {
        elements.queueCount.textContent = state.queueCount;
    }

    if (elements.queueList) {
        if (state.queue.length === 0) {
            elements.queueList.innerHTML = '<div class="queue-empty">No items in queue</div>';
        } else {
            elements.queueList.innerHTML = state.queue.map(item => `
                <div class="queue-item" data-url="${escapeHtml(item.url)}">
                    <span class="queue-item-url">${escapeHtml(truncate(item.url, 60))}</span>
                    <span class="queue-item-type">${item.type}</span>
                    <button class="btn btn-small btn-ghost btn-remove-queue" data-url="${escapeHtml(item.url)}">✕</button>
                </div>
            `).join('');

            // Add remove handlers
            elements.queueList.querySelectorAll('.btn-remove-queue').forEach(btn => {
                btn.addEventListener('click', () => removeFromQueue(btn.dataset.url));
            });
        }
    }
}


// =============================================
// API Functions
// =============================================

async function startDownload(type) {
    const url = elements.urlInput?.value?.trim();

    if (!url) {
        showToast('Please enter a URL', 'error');
        return;
    }

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, type })
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            elements.urlInput.value = '';
            // Immediately update type in state for UI feedback
            state.downloadType = type;
        } else {
            showToast(result.message || 'Download failed', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function cancelDownload() {
    try {
        await fetch('/api/download/cancel', { method: 'POST' });
        showToast('Download cancelled', 'info');
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function pauseDownload() {
    const isPaused = state.status === 'paused';
    const endpoint = isPaused ? '/api/download/resume' : '/api/download/pause';

    try {
        await fetch(endpoint, { method: 'POST' });
        showToast(isPaused ? 'Download resumed' : 'Download paused', 'info');
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function removeFromQueue(url) {
    try {
        await fetch(`/api/queue/${encodeURIComponent(url)}`, { method: 'DELETE' });
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function clearQueue() {
    if (!confirm('Clear all items from queue?')) return;

    try {
        await fetch('/api/queue', { method: 'DELETE' });
        showToast('Queue cleared', 'success');
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function openDownloads() {
    try {
        const response = await fetch('/api/system/open/downloads');
        const result = await response.json();

        if (!result.success) {
            // Show the actual message from the server if available
            const message = result.message || 'Could not open downloads folder';
            showToast(message, 'info');
        } else {
            showToast(result.message || 'Downloads folder opened', 'success');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function openDocs() {
    try {
        const response = await fetch('/api/system/open/docs');
        const result = await response.json();

        if (!result.success) {
            // Show the actual message from the server if available
            const message = result.message || 'Could not open docs folder';
            showToast(message, 'info');
        } else {
            showToast(result.message || 'Docs folder opened', 'success');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function playLatest() {
    try {
        const response = await fetch('/api/system/play-latest');
        const result = await response.json();

        if (result.success) {
            showToast(`Playing: ${result.file.split('/').pop()}`, 'success');
        } else {
            const message = result.message || 'No media files found';
            showToast(message, 'info');
        }
    } catch (error) {
        if (error.message.includes('404')) {
            showToast('No media files found in downloads', 'info');
        } else {
            showToast('Error: ' + error.message, 'error');
        }
    }
}

async function exitApp() {
    if (!confirm('Are you sure you want to exit?')) return;

    try {
        await fetch('/api/system/exit', { method: 'POST' });
        showToast('Shutting down...', 'info');
    } catch (error) {
        // Expected - server will close
    }
}




// =============================================
// Session Management
// =============================================

async function checkSession() {
    try {
        const response = await fetch('/api/queue/session');
        const data = await response.json();

        if (data.needed) {
            if (elements.sessionQueueCount) elements.sessionQueueCount.textContent = data.queue_count;
            if (elements.sessionFailedCount) elements.sessionFailedCount.textContent = data.failed_count;

            elements.sessionModal?.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error checking session:', error);
    }
}

async function handleSessionAction(action) {
    try {
        const response = await fetch('/api/queue/session/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            elements.sessionModal?.classList.add('hidden');

            // Trigger a refresh of status and queue
            fetchInitialStatus();
        } else {
            showToast('Error: ' + result.message, 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

async function toggleSessionDetails() {
    if (!elements.sessionDetails || !elements.sessionUrlList) return;

    const isHidden = elements.sessionDetails.classList.contains('hidden');

    if (isHidden) {
        // Fetch and render
        try {
            const response = await fetch('/api/queue/status');
            const data = await response.json();

            elements.sessionUrlList.innerHTML = '';

            // Combine and render
            const items = [
                ...data.queued_urls.map(u => ({ ...u, status: 'queued' })),
                ...data.failed_urls.map(u => ({ ...u, status: 'failed' }))
            ];

            if (items.length === 0) {
                elements.sessionUrlList.innerHTML = '<div class="empty-state">No items found</div>';
            } else {
                items.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'session-url-item';
                    div.innerHTML = `
                        <span class="session-url-text" title="${item.url}">${item.url}</span>
                        <span class="session-url-badge ${item.status}">${item.status}</span>
                    `;
                    elements.sessionUrlList.appendChild(div);
                });
            }

            elements.sessionDetails.classList.remove('hidden');
            elements.btnSessionShow.textContent = 'Hide Details';
        } catch (error) {
            console.error('Error fetching session details:', error);
            showToast('Failed to load details', 'error');
        }
    } else {
        elements.sessionDetails.classList.add('hidden');
        elements.btnSessionShow.innerHTML = '<span class="btn-icon">👁️</span> Show Details';
    }
}


// =============================================
// Theme Switcher
// =============================================

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    console.log(`Theme toggled to: ${newTheme}`);
}


// =============================================
// Toast Notifications
// =============================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Make showToast available globally for templates
window.showToast = showToast;


// =============================================
// Utility Functions
// =============================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(str, maxLength) {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength) + '...';
}


// =============================================
// Event Handlers
// =============================================

function setupEventHandlers() {
    // Download buttons
    elements.btnVideo?.addEventListener('click', () => startDownload('video'));
    elements.btnAudio?.addEventListener('click', () => startDownload('audio'));

    // URL input - Enter key
    elements.urlInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            startDownload('video');
        }
    });

    // Action buttons
    elements.btnDownloads?.addEventListener('click', openDownloads);
    elements.btnDocs?.addEventListener('click', openDocs);
    elements.btnPlayLatest?.addEventListener('click', playLatest);
    elements.btnExit?.addEventListener('click', exitApp);

    // Download controls
    elements.btnCancel?.addEventListener('click', cancelDownload);
    elements.btnPause?.addEventListener('click', pauseDownload);

    // Theme toggle
    elements.btnThemeToggle?.addEventListener('click', toggleTheme);

    // Session Modal actions
    elements.btnSessionDelete?.addEventListener('click', () => handleSessionAction('delete'));
    elements.btnSessionIgnore?.addEventListener('click', () => handleSessionAction('ignore'));
    elements.btnSessionContinue?.addEventListener('click', () => handleSessionAction('continue'));
    elements.btnSessionShow?.addEventListener('click', toggleSessionDetails);

    // Queue controls
    elements.btnClearQueue?.addEventListener('click', clearQueue);
}


// =============================================
// WebSocket Event Handlers
// =============================================

function setupWebSocketHandlers(wsManager) {
    wsManager.on('initial_state', (data) => {
        if (data.settings) {
            state.settings = data.settings;
        }
        if (data.status) {
            state.downloadType = data.status.download_type;
            updateStatus(data.status.status, data.status.status_message);

            const isTerminal = ['completed', 'idle', 'cancelled', 'error'].includes(data.status.status);
            if (data.status.progress && !isTerminal) {
                updateProgress(data.status.progress);
            }
        }
        if (data.queue) {
            updateQueue(data.queue);
        }
    });

    wsManager.on('status_update', (data) => {
        console.log('Received status_update:', data.status, data.status_message);
        if (data.download_type) {
            state.downloadType = data.download_type;
        }
        updateStatus(data.status, data.status_message);

        // Only update progress if we're not in a terminal state
        const isTerminal = ['completed', 'idle', 'cancelled', 'error'].includes(data.status);
        if (data.progress && !isTerminal) {
            updateProgress(data.progress);
        }
    });

    wsManager.on('queue_update', (data) => {
        updateQueue(data);
    });

    wsManager.on('download_complete', (data) => {
        showToast(`Download complete: ${data.files?.[0] || 'Success'}`, 'success');
    });

    wsManager.on('download_failed', (data) => {
        showToast(`Download failed: ${data.error || 'Unknown error'}`, 'error');
    });

    wsManager.on('disconnected', () => {
        console.log('WebSocket disconnected');
    });
}


// =============================================
// Initialization
// =============================================

let wsManager = null;
let isInitialized = false;

function initApp() {
    if (isInitialized) return;
    isInitialized = true;

    console.log('Initializing App...');
    cacheElements();
    setupEventHandlers();

    // Initialize WebSocket
    wsManager = new WebSocketManager();
    setupWebSocketHandlers(wsManager);
    wsManager.connect();

    // Initial status fetch
    fetchInitialStatus();
    checkSession();
}

async function fetchInitialStatus() {
    try {
        // Fetch current download status
        const statusResponse = await fetch('/api/download/status');
        const statusData = await statusResponse.json();

        updateStatus(statusData.status, statusData.status_message);

        const isTerminal = ['completed', 'idle', 'cancelled', 'error'].includes(statusData.status);
        if (statusData.progress && !isTerminal) {
            updateProgress(statusData.progress);
        }

        // Fetch queue status
        const queueResponse = await fetch('/api/queue/status');
        const queueData = await queueResponse.json();

        updateQueue(queueData);
    } catch (error) {
        console.error('Failed to fetch initial status:', error);
    }
}

// Auto-initialize on DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    // DOM already loaded
    initApp();
}
