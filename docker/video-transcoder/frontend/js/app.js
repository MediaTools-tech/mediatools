
// State
let selectedFile = null;
let currentJobId = null;
let pollingInterval = null;

// DOM Elements Cache
const elements = {
    videoInput: document.getElementById('video-input'),
    uploadArea: document.getElementById('upload-area'),
    uploadBtn: document.getElementById('upload-btn'),
    progressSection: document.getElementById('progress-section'),
    uploadSection: document.getElementById('upload-section'),
    jobFilename: document.getElementById('job-filename'),
    jobId: document.getElementById('job-id'),
    jobStatus: document.getElementById('job-status'),
    progressFill: document.getElementById('progress-fill'),
    downloadBtn: document.getElementById('download-btn'),
    newJobBtn: document.getElementById('new-job-btn'),
    jobsList: document.getElementById('jobs-list'),
    refreshJobsBtn: document.getElementById('refresh-jobs-btn'),
    cancelJobBtn: document.getElementById('cancel-job-btn'),
    customOptionsArea: document.getElementById('custom-options-area'),
    videoCodec: document.getElementById('video-codec'),
    container: document.getElementById('container'),
    audioCodec: document.getElementById('audio-codec'),
    crf: document.getElementById('crf'),
    customCrfContainer: document.getElementById('custom-crf-container'),
    customCrfInput: document.getElementById('custom-crf'),
    defaultSettingsRadio: document.getElementById('default-settings'),
    customSettingsRadio: document.getElementById('custom-settings'),
    // Group of all settings controls for easy toggling
    settingsControls: [
        'video-codec', 'resolution', 'sharpening',
        'container', 'audio-codec', 'crf', 'custom-crf'
    ].map(id => document.getElementById(id))
};

// Compatibility Mappings
const VIDEO_CODEC_MAP = {
    "default": "libx264",
    "h264": "libx264",
    "h265": "libx265",
    "av1": "libaom-av1",
    "vp9": "libvpx-vp9"
};

const CONTAINER_MAP = {
    "libx264": ["mp4", "mkv", "avi", "mov"],
    "libx265": ["mp4", "mkv", "mov"],
    "libaom-av1": ["mkv", "webm"],
    "libvpx-vp9": ["mkv", "webm"]
};

const AUDIO_CODEC_MAP = {
    "mp4": ["aac", "mp3", "ac3"],
    "mkv": ["aac", "mp3", "ac3", "opus", "flac", "vorbis"],
    "webm": ["opus", "vorbis"],
    "mov": ["aac", "mp3", "ac3"],
    "avi": ["mp3", "ac3"]
};

const CRF_MAP = {
    'low': { 'h264': 27, 'h265': 29, 'vp9': 37, 'av1': 39 },
    'standard': { 'h264': 23, 'h265': 25, 'vp9': 32, 'av1': 34 },
    'high': { 'h264': 19, 'h265': 21, 'vp9': 27, 'av1': 29 },
    'visually_lossless': { 'h264': 15, 'h265': 17, 'vp9': 23, 'av1': 24 }
};

/**
 * Initialization
 */
document.addEventListener('DOMContentLoaded', () => {
    try {
        setupEventListeners();
        loadJobs();
        // Initialize dropdowns immediately
        updateContainerOptions();
        updateCrfOptions();
        // Ensure settings state is correctly applied on load
        toggleSettingsState();
    } catch (e) {
        console.error('Initialization error:', e);
    }
});

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
    // File upload area
    if (elements.uploadArea) {
        elements.uploadArea.addEventListener('click', () => elements.videoInput.click());

        elements.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.uploadArea.classList.add('dragover');
        });

        elements.uploadArea.addEventListener('dragleave', () => elements.uploadArea.classList.remove('dragover'));

        elements.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                selectedFile = files[0];
                updateUploadUI();
            }
        });
    }

    if (elements.videoInput) elements.videoInput.addEventListener('change', handleFileSelect);

    // Main action buttons
    if (elements.uploadBtn) elements.uploadBtn.addEventListener('click', uploadVideo);
    if (elements.downloadBtn) elements.downloadBtn.addEventListener('click', downloadVideo);
    if (elements.newJobBtn) elements.newJobBtn.addEventListener('click', resetUpload);
    if (elements.refreshJobsBtn) elements.refreshJobsBtn.addEventListener('click', loadJobs);
    if (elements.cancelJobBtn) elements.cancelJobBtn.addEventListener('click', cancelJob);

    // Settings Mode Toggling
    if (elements.defaultSettingsRadio) elements.defaultSettingsRadio.addEventListener('change', toggleSettingsState);
    if (elements.customSettingsRadio) elements.customSettingsRadio.addEventListener('change', toggleSettingsState);

    // Cascading Option updates
    if (elements.videoCodec) {
        elements.videoCodec.addEventListener('change', () => {
            updateContainerOptions();
            updateCrfOptions();
        });
    }

    if (elements.container) {
        elements.container.addEventListener('change', () => {
            updateAudioCodecOptions();
        });
    }

    // CRF Custom Value Toggle
    if (elements.crf) {
        elements.crf.addEventListener('change', syncCustomCrfVisibility);
    }
}

/**
 * UI State Logic
 */
function syncCustomCrfVisibility() {
    if (!elements.crf || !elements.customCrfContainer) return;
    const isCustomValue = elements.crf.value === 'custom';
    elements.customCrfContainer.style.display = isCustomValue ? 'block' : 'none';
}

/**
 * UI State Logic
 */
function toggleSettingsState() {
    const isCustom = elements.customSettingsRadio && elements.customSettingsRadio.checked;

    // If switching to Default, reset all values to reference defaults
    if (!isCustom) {
        if (elements.videoCodec) elements.videoCodec.value = 'default';
        if (elements.container) elements.container.value = 'default';
        if (elements.audioCodec) elements.audioCodec.value = 'default';

        // Reset CRF to Standard profile (which is index 0 in updateCrfOptions)
        if (elements.crf) elements.crf.selectedIndex = 0;
        if (elements.customCrfContainer) elements.customCrfContainer.style.display = 'none';

        const res = document.getElementById('resolution');
        if (res) res.value = 'default';
        const sharp = document.getElementById('sharpening');
        if (sharp) sharp.value = 'none';

        // Trigger cascade to refresh dependencies (Container list, CRF list)
        updateContainerOptions();
        updateCrfOptions();
    }

    elements.settingsControls.forEach(control => {
        if (control) control.disabled = !isCustom;
    });

    // When enabling custom settings, ensure CRF is set to Standard if it's currently 'custom'
    if (isCustom && elements.crf && elements.crf.value === 'custom') {
        elements.crf.selectedIndex = 0; // Default to Standard
    }

    // Final visibility check for custom CRF
    syncCustomCrfVisibility();
}

/**
 * Option Dropdown Logic
 */
function updateContainerOptions() {
    if (!elements.container || !elements.videoCodec) return;

    const vCodec = elements.videoCodec.value;
    const backendVCodec = VIDEO_CODEC_MAP[vCodec] || 'libx264';
    const compatible = CONTAINER_MAP[backendVCodec] || ['mp4'];
    const currentVal = elements.container.value;

    elements.container.innerHTML = '';

    // Only add Default (mp4) if Video Codec itself is "default"
    if (vCodec === 'default') {
        const defOpt = document.createElement('option');
        defOpt.value = 'default';
        defOpt.textContent = 'Default (mp4)';
        elements.container.appendChild(defOpt);
    }

    compatible.forEach(c => {
        if (vCodec === 'default' && c === 'mp4') return; // mp4 handled by 'default' label
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c.toUpperCase();
        elements.container.appendChild(opt);
    });

    // MAINTAIN/RESET SELECTION
    // If current value is still valid in new list, keep it. 
    // Otherwise, pick first available.
    const validValues = Array.from(elements.container.options).map(o => o.value);
    if (!validValues.includes(currentVal)) {
        elements.container.value = validValues[0];
    } else {
        elements.container.value = currentVal;
    }

    // Always trigger next step in cascade
    updateAudioCodecOptions();
}

function updateAudioCodecOptions() {
    if (!elements.audioCodec || !elements.container) return;

    const containerVal = elements.container.value;
    const effContainer = containerVal === 'default' ? 'mp4' : containerVal;
    const compatible = AUDIO_CODEC_MAP[effContainer] || ['aac'];
    const currentVal = elements.audioCodec.value;

    elements.audioCodec.innerHTML = '';

    // Only add Default (aac) if Container itself is "default"
    if (containerVal === 'default') {
        const defOpt = document.createElement('option');
        defOpt.value = 'default';
        defOpt.textContent = 'Default (aac)';
        elements.audioCodec.appendChild(defOpt);
    }

    // Always keep "Copy Original" as it's a global feature
    const copyOpt = document.createElement('option');
    copyOpt.value = 'copy';
    copyOpt.textContent = 'Copy Original';
    elements.audioCodec.appendChild(copyOpt);

    compatible.forEach(a => {
        if (containerVal === 'default' && a === 'aac') return; // aac handled by 'default' label
        const opt = document.createElement('option');
        opt.value = a;
        opt.textContent = a.toUpperCase();
        elements.audioCodec.appendChild(opt);
    });

    const validValues = Array.from(elements.audioCodec.options).map(o => o.value);
    if (!validValues.includes(currentVal)) {
        elements.audioCodec.value = validValues[0];
    } else {
        elements.audioCodec.value = currentVal;
    }
}

function updateCrfOptions() {
    if (!elements.crf || !elements.videoCodec) return;

    const vCodec = elements.videoCodec.value;
    const backendVCodec = VIDEO_CODEC_MAP[vCodec] || 'libx264';

    let codecKey = 'h264';
    if (backendVCodec.includes('x265')) codecKey = 'h265';
    else if (backendVCodec.includes('vp9')) codecKey = 'vp9';
    else if (backendVCodec.includes('av1')) codecKey = 'av1';

    const prevVal = elements.crf.value;
    const prevProfile = elements.crf.options[elements.crf.selectedIndex]?.dataset.profile;

    elements.crf.innerHTML = '';

    const profiles = [
        { id: 'standard', label: 'Standard' },
        { id: 'high', label: 'High Quality' },
        { id: 'low', label: 'Low Quality' },
        { id: 'visually_lossless', label: 'Visually Lossless' }
    ];

    profiles.forEach(p => {
        const val = CRF_MAP[p.id][codecKey];
        if (val === undefined) return;

        const opt = document.createElement('option');
        opt.value = val;
        opt.dataset.profile = p.id;
        opt.textContent = `${p.label} (CRF ${val})`;
        elements.crf.appendChild(opt);
    });

    // Add Custom Value option
    const customOpt = document.createElement('option');
    customOpt.value = 'custom';
    customOpt.textContent = 'Custom Value';
    elements.crf.appendChild(customOpt);

    // Re-select by profile (preferred) or value
    const options = Array.from(elements.crf.options);
    const match = options.find(o => o.dataset.profile === prevProfile) || options.find(o => o.value === prevVal);

    if (match) {
        elements.crf.value = match.value;
    } else {
        elements.crf.selectedIndex = 0; // Default to Standard
    }

    // Ensure input field visibility matches new selection
    syncCustomCrfVisibility();
}

/**
 * File & Upload Logic
 */
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        selectedFile = files[0];
        updateUploadUI();
    }
}

function updateUploadUI() {
    if (selectedFile && elements.uploadArea) {
        elements.uploadArea.querySelector('.upload-content').innerHTML = `
            <span class="upload-icon">✅</span>
            <p><strong>${selectedFile.name}</strong></p>
            <p class="upload-hint">${formatFileSize(selectedFile.size)}</p>
        `;
        if (elements.uploadBtn) elements.uploadBtn.disabled = false;
    }
}

async function uploadVideo() {
    if (!selectedFile) return;

    if (elements.uploadBtn) {
        elements.uploadBtn.disabled = true;
        elements.uploadBtn.textContent = 'Uploading...';
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    // Always gather options from the visible form
    const options = getTranscodingOptions();

    // Validation: Check for empty custom CRF
    const isCustom = elements.customSettingsRadio && elements.customSettingsRadio.checked;
    if (isCustom && elements.crf && elements.crf.value === 'custom') {
        const customValue = elements.customCrfInput ? elements.customCrfInput.value.trim() : "";
        if (!customValue || isNaN(parseInt(customValue, 10)) || parseInt(customValue, 10) < 0 || parseInt(customValue, 10) > 51) {
            alert('Please enter a valid CRF value between 0 and 51.');
            if (elements.uploadBtn) {
                elements.uploadBtn.disabled = false;
                elements.uploadBtn.textContent = 'Upload & Transcode';
            }
            if (elements.customCrfInput) elements.customCrfInput.focus();
            return;
        }
    }

    formData.append('options', JSON.stringify(options));

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const job = await response.json();
        currentJobId = job.job_id;

        // Switch View
        if (elements.uploadSection) elements.uploadSection.style.display = 'none';
        if (elements.progressSection) elements.progressSection.style.display = 'block';

        // Set Info
        if (elements.jobFilename) elements.jobFilename.textContent = job.filename;
        if (elements.jobId) elements.jobId.textContent = job.job_id;

        startPolling();
    } catch (error) {
        alert('Upload failed: ' + error.message);
        if (elements.uploadBtn) {
            elements.uploadBtn.disabled = false;
            elements.uploadBtn.textContent = 'Upload & Transcode';
        }
    }
}

function getTranscodingOptions() {
    const isCustom = elements.customSettingsRadio && elements.customSettingsRadio.checked;

    // If "Default" is selected, return default values
    if (!isCustom) {
        return {
            video_codec: "default",
            resolution: "default",
            sharpening: "none",
            container: "default",
            audio_codec: "default",
            crf: 23 // Standard H.264 default
        };
    }

    // Otherwise, return manually selected values
    let crfVal = parseInt(elements.crf.value, 10);
    if (elements.crf.value === 'custom') {
        crfVal = parseInt(elements.customCrfInput.value, 10) || 23;
    }

    return {
        video_codec: elements.videoCodec.value,
        resolution: document.getElementById('resolution').value,
        sharpening: document.getElementById('sharpening').value,
        container: elements.container.value,
        audio_codec: elements.audioCodec.value,
        crf: crfVal
    };
}

/**
 * Job Status Polling
 */
function startPolling() {
    updateJobStatus();
    pollingInterval = setInterval(updateJobStatus, 2000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function updateJobStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/jobs/${currentJobId}`);
        if (!response.ok) throw new Error('Failed to fetch job status');

        const job = await response.json();

        if (elements.jobStatus) {
            elements.jobStatus.textContent = job.status;
            elements.jobStatus.className = `status-badge status-${job.status}`;
        }

        if (elements.progressFill) {
            elements.progressFill.style.width = `${job.progress}%`;
            elements.progressFill.textContent = `${job.progress}%`;
        }

        if (job.status === 'completed') {
            stopPolling();
            if (elements.newJobBtn) elements.newJobBtn.style.display = 'block';
            loadJobs();
        } else if (job.status === 'cancelled') {
            stopPolling();
            if (elements.cancelJobBtn) elements.cancelJobBtn.style.display = 'none';
            if (elements.newJobBtn) elements.newJobBtn.style.display = 'block';
            loadJobs();
        } else if (job.status === 'failed') {
            stopPolling();
            alert('Transcoding failed: ' + (job.error_message || 'Unknown error'));
            if (elements.newJobBtn) elements.newJobBtn.style.display = 'block';
        }
    } catch (error) {
        console.error('Status fetch error:', error);
    }
}

async function cancelJob() {
    if (!currentJobId) return;
    if (!confirm('Are you sure you want to cancel this job?')) return;

    try {
        const response = await fetch(`/api/jobs/${currentJobId}/cancel`, { method: 'POST' });
        if (!response.ok) throw new Error('Cancellation failed');

        alert('Job cancellation initiated.');
        if (elements.cancelJobBtn) {
            elements.cancelJobBtn.disabled = true;
            elements.cancelJobBtn.textContent = 'Cancelling...';
        }
    } catch (error) {
        alert('Could not cancel job: ' + error.message);
    }
}

/**
 * Downloads
 */
function downloadVideo() {
    if (!currentJobId) return;
    window.location.href = `/api/jobs/${currentJobId}/download`;
}

/**
 * UI Reset
 */
function resetUpload() {
    selectedFile = null;
    currentJobId = null;
    stopPolling();

    if (elements.uploadSection) elements.uploadSection.style.display = 'block';
    if (elements.progressSection) elements.progressSection.style.display = 'none';

    if (elements.cancelJobBtn) {
        elements.cancelJobBtn.style.display = 'block';
        elements.cancelJobBtn.disabled = false;
        elements.cancelJobBtn.textContent = 'Cancel Job';
    }

    if (elements.newJobBtn) elements.newJobBtn.style.display = 'none';

    if (elements.uploadBtn) {
        elements.uploadBtn.disabled = true;
        elements.uploadBtn.textContent = 'Upload & Transcode';
    }

    if (elements.uploadArea) {
        elements.uploadArea.querySelector('.upload-content').innerHTML = `
            <span class="upload-icon">📁</span>
            <p>Click to select or drag and drop a video file</p>
            <p class="upload-hint">Supported: MP4, AVI, MOV, MKV</p>
        `;
    }

    if (elements.videoInput) elements.videoInput.value = '';
    loadJobs();
}

/**
 * Job History
 */
async function loadJobs() {
    try {
        const response = await fetch('/api/jobs/?limit=10');
        const data = await response.json();
        renderJobs(data.jobs);
    } catch (error) {
        console.error('Error loading jobs:', error);
    }
}

function renderJobs(jobs) {
    if (!elements.jobsList) return;
    if (jobs.length === 0) {
        elements.jobsList.innerHTML = '<p class="empty-state">No jobs yet.</p>';
        return;
    }

    elements.jobsList.innerHTML = jobs.map(job => `
        <div class="job-item">
            <div class="job-details">
                <p><strong>${job.filename}</strong></p>
                <p>Status: <span class="status-badge status-${job.status}">${job.status}</span></p>
                <p>Created: ${formatDate(job.created_at)}</p>
            </div>
            <div class="job-actions">
                ${job.status === 'completed' ? `<button class="btn btn-small btn-success" onclick="downloadJobById('${job.job_id}')">Download</button>` : ''}
                ${job.status === 'processing' ? `<button class="btn btn-small" onclick="viewJob('${job.job_id}')">View (${job.progress}%)</button>` : ''}
            </div>
        </div>
    `).join('');
}

// Global scope helpers for onclick
window.downloadJobById = (jobId) => window.location.href = `/api/jobs/${jobId}/download`;
window.viewJob = (jobId) => {
    currentJobId = jobId;
    if (elements.uploadSection) elements.uploadSection.style.display = 'none';
    if (elements.progressSection) elements.progressSection.style.display = 'block';
    startPolling();
};

/**
 * Utils
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(ds) {
    return new Date(ds).toLocaleString();
}