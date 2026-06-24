// Global variables
let map;
let markers = [];
let activeIssueId = null;
let activeIssueData = null;

// Default coordinates (centered on seeded Bangalore area)
const defaultLat = 12.9716;
const defaultLng = 77.5946;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadIssues();
});

// Initialize Leaflet Map
function initMap() {
    // Dark mode tiles from CartoDB (completely free, no API key needed)
    map = L.map('map').setView([defaultLat, defaultLng], 15);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Map Click: Open report modal with coordinates
    map.on('click', (e) => {
        openReportModal(e.latlng.lat, e.latlng.lng);
    });
}

// Generate Custom Div Icons for Leaflet based on category
function getCategoryIcon(category, intensity) {
    let color = '#4facfe'; // default blue
    if (category === 'Roads') color = '#00f2fe'; // electric teal
    else if (category === 'Water & Sewerage') color = '#38bdf8'; // light blue
    else if (category === 'Waste Management') color = '#a78bfa'; // lavender
    else if (category === 'Streetlights') color = '#fbbf24'; // amber
    else if (category === 'Utilities') color = '#f87171'; // soft red
    else color = '#9ca3af'; // gray

    let size = 14;
    if (intensity === 'High') size = 20;
    else if (intensity === 'Medium') size = 16;

    const html = `<div style="background-color: ${color}; width: ${size}px; height: ${size}px; border-radius: 50%; border: 3px solid #0a0e17; box-shadow: 0 0 12px ${color};"></div>`;
    
    return L.divIcon({
        className: 'custom-map-pin',
        html: html,
        iconSize: [size, size],
        iconAnchor: [size/2, size/2]
    });
}

// Load and plot issues
function loadIssues() {
    fetch('/api/issues')
        .then(response => response.json())
        .then(data => {
            // Clear existing markers
            markers.forEach(m => map.removeLayer(m));
            markers = [];

            data.forEach(issue => {
                const marker = L.marker([issue.latitude, issue.longitude], {
                    icon: getCategoryIcon(issue.category, issue.intensity)
                }).addTo(map);

                marker.on('click', () => {
                    selectIssue(issue);
                });

                // Tooltip on hover
                marker.bindTooltip(`
                    <strong style="color:#f3f4f6; font-family:'Outfit';">${issue.title}</strong><br>
                    <span style="color:#9ca3af; font-size:0.8rem;">${issue.category} | ${issue.status}</span>
                `, {
                    direction: 'top',
                    opacity: 0.9,
                    className: 'glass-tooltip'
                });

                markers.push(marker);
            });
        })
        .catch(err => console.error('Error fetching issues:', err));
}

// Select issue and show details in sidebar
function selectIssue(issue) {
    activeIssueId = issue.id;
    activeIssueData = issue;
    
    document.getElementById('sidebar-placeholder').style.display = 'none';
    const details = document.getElementById('sidebar-details');
    details.style.display = 'flex';

    // Populate data
    document.getElementById('issue-title').innerText = issue.title;
    
    const catBadge = document.getElementById('issue-category');
    catBadge.innerText = issue.category;
    catBadge.className = 'badge';
    
    // Customize badge style based on category
    let catClass = 'badge-other';
    if (issue.category === 'Roads') catClass = 'low';
    else if (issue.category === 'Streetlights') catClass = 'medium';
    else if (issue.category === 'Waste Management') catClass = 'high';
    catBadge.classList.add(catClass);

    const intBadge = document.getElementById('issue-intensity');
    intBadge.innerText = `${issue.intensity} Intensity`;
    intBadge.className = 'badge ' + issue.intensity.toLowerCase();

    const statBadge = document.getElementById('issue-status');
    statBadge.innerText = issue.status;
    statBadge.className = 'badge status-' + issue.status.toLowerCase().replace(' ', '-');

    document.getElementById('issue-desc').innerText = issue.description;
    document.getElementById('issue-reporter').innerText = issue.reporter;
    document.getElementById('issue-reporter-points').innerText = issue.reporter_points;
    document.getElementById('issue-date').innerText = issue.created_at;
    document.getElementById('issue-score').innerText = issue.score;

    // Image/Video preview
    const imgEl = document.getElementById('issue-image');
    const videoEl = document.getElementById('issue-video');
    if (issue.image_url) {
        const fileExt = issue.image_url.split('.').pop().toLowerCase();
        const isVideo = ['mp4', 'mov', 'avi'].includes(fileExt);
        if (isVideo) {
            videoEl.src = issue.image_url;
            videoEl.style.display = 'block';
            imgEl.style.display = 'none';
        } else {
            imgEl.src = issue.image_url;
            imgEl.style.display = 'block';
            videoEl.style.display = 'none';
        }
    } else {
        imgEl.style.display = 'none';
        videoEl.style.display = 'none';
    }

    // Update vote buttons active state
    updateVoteButtons(issue.user_vote);

    // Load comments
    renderComments(issue.comments);

    // Load status timeline logs
    renderTimeline(issue.logs);
}

function deselectIssue() {
    activeIssueId = null;
    activeIssueData = null;
    document.getElementById('sidebar-details').style.display = 'none';
    document.getElementById('sidebar-placeholder').style.display = 'flex';
}

function updateVoteButtons(userVote) {
    const upBtn = document.querySelector('.vote-btn.upvote');
    const downBtn = document.querySelector('.vote-btn.downvote');
    
    upBtn.classList.remove('active');
    downBtn.classList.remove('active');
    
    if (userVote === 'upvote') upBtn.classList.add('active');
    if (userVote === 'downvote') downBtn.classList.add('active');
}

// Render comments list
function renderComments(comments) {
    const list = document.getElementById('issue-comments');
    list.innerHTML = '';
    
    if (comments.length === 0) {
        list.innerHTML = '<p style="color:var(--text-muted); font-size:0.8rem; text-align:center; padding: 0.5rem 0;">No comments yet.</p>';
        return;
    }

    comments.forEach(c => {
        const item = document.createElement('div');
        item.className = 'comment-item';
        item.innerHTML = `
            <div class="comment-meta">
                <strong>@${c.author}</strong>
                <span>${c.created_at}</span>
            </div>
            <div class="comment-content">${c.content}</div>
        `;
        list.appendChild(item);
    });
}

// Render timeline logs
function renderTimeline(logs) {
    const timeline = document.getElementById('issue-timeline');
    timeline.innerHTML = '';

    logs.forEach(log => {
        const item = document.createElement('div');
        item.className = 'timeline-item';
        
        let statusBadge = '';
        if (log.status_update) {
            statusBadge = `<span class="badge status-${log.status_update.toLowerCase().replace(' ', '-')}" style="transform: scale(0.85); transform-origin: left; margin-bottom: 2px;">${log.status_update}</span><br>`;
        }

        item.innerHTML = `
            <div class="timeline-meta"><strong>@${log.author}</strong> on ${log.created_at}</div>
            <div class="timeline-text">${statusBadge}${log.content}</div>
        `;
        timeline.appendChild(item);
    });
}

// Vote handling
function castVote(voteType) {
    if (!activeIssueId) return;

    fetch(`/api/issues/${activeIssueId}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vote_type: voteType })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('issue-score').innerText = data.score;
            
            // Toggle active status UI
            let newUserVote = null;
            if (data.action === 'voted') newUserVote = voteType;
            else if (data.action === 'switched') newUserVote = voteType;
            // retraction leaves userVote as null
            
            updateVoteButtons(newUserVote);
            
            // Update points navbar locally if possible, or reload list
            loadIssues();
        }
    })
    .catch(err => console.error('Error voting:', err));
}

// Comment submission
function submitComment() {
    if (!activeIssueId) return;
    const input = document.getElementById('new-comment-text');
    const content = input.value.trim();
    if (!content) return;

    fetch(`/api/issues/${activeIssueId}/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            input.value = '';
            // Refresh comments on the page
            activeIssueData.comments.push(data.comment);
            renderComments(activeIssueData.comments);
            
            // Increment user points badge locally
            const pointsBadge = document.getElementById('nav-user-points');
            if (pointsBadge) {
                const currentVal = parseInt(pointsBadge.innerText) || 0;
                pointsBadge.innerText = (currentVal + 2) + ' pts';
            }
        } else {
            alert(data.error);
        }
    })
    .catch(err => console.error(err));
}

// Modal handling
function openReportModal(lat, lng) {
    document.getElementById('report-lat').value = lat.toFixed(6);
    document.getElementById('report-lng').value = lng.toFixed(6);
    
    // Clear other form fields
    document.getElementById('report-title').value = '';
    document.getElementById('report-desc').value = '';
    document.getElementById('report-image').value = '';
    document.getElementById('report-intensity').value = 'Medium';
    
    document.getElementById('report-modal').classList.add('show');
}

function openReportModalWithDefault() {
    openReportModal(defaultLat, defaultLng);
}

function closeReportModal() {
    document.getElementById('report-modal').classList.remove('show');
}

// Issue report submission
function handleReportSubmit(e) {
    e.preventDefault();
    const form = document.getElementById('report-form');
    const formData = new FormData(form);

    fetch('/api/issues/report', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeReportModal();
            loadIssues();
            
            // Show auto categorization success message in alerts
            alert(data.message);
            
            // Refresh points indicator
            const pointsBadge = document.getElementById('nav-user-points');
            if (pointsBadge) {
                const currentVal = parseInt(pointsBadge.innerText) || 0;
                pointsBadge.innerText = (currentVal + 15) + ' pts';
            }
        } else {
            alert(data.error || 'Failed to submit issue report.');
        }
    })
    .catch(err => {
        console.error(err);
        alert('Error connecting to server.');
    });
}
