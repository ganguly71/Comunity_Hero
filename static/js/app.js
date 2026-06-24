// Global variables
let map;
let markers = [];
let activeIssueId = null;
let activeIssueData = null;
let allIssues = [];
let currentUserLocation = null;

// Default coordinates (centered on seeded Bangalore area)
const defaultLat = 12.9716;
const defaultLng = 77.5946;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadIssues();
});

// Initialize Leaflet Map
function initMap() {
    // Create map instance with zoom constraints
    map = L.map('map', { minZoom: 2, maxZoom: 18 }).setView([defaultLat, defaultLng], 15);

    // Esri World Imagery (Vibrant Satellite)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19
    }).addTo(map);
    
    // Transparent street labels overlay for hybrid satellite view
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Attempt to center map on user's current location and place a marker
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
            const userLat = position.coords.latitude;
            const userLng = position.coords.longitude;
            currentUserLocation = [userLat, userLng];
            map.setView([userLat, userLng], 15);
            
            // Add a special glowing pulse marker for current location
            const userIcon = L.divIcon({
                className: 'user-location-marker',
                html: '<div style="background-color: #00f2fe; width: 14px; height: 14px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 0 16px #00f2fe; animation: pulse 2s infinite;"></div>',
                iconSize: [14, 14],
                iconAnchor: [7, 7]
            });
            
            L.marker([userLat, userLng], { icon: userIcon })
                .addTo(map)
                .bindTooltip("You are here", { permanent: false, direction: 'top' });
                
        }, (err) => {
            console.warn("Geolocation service failed or permission denied. Defaulting coordinates.");
        });
    }

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
            allIssues = data;
            renderMarkers();
        })
        .catch(err => console.error('Error fetching issues:', err));
}

// Render markers on the map dynamically supporting status filters
function renderMarkers() {
    // Clear existing markers
    markers.forEach(m => map.removeLayer(m));
    markers = [];

    const showResolved = document.getElementById('toggle-resolved').checked;

    allIssues.forEach(issue => {
        // Skip resolved issues if filter checkbox is not active
        if (issue.status === 'Resolved' && !showResolved) {
            return;
        }

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

    // Image/Video preview (supporting multiple media files)
    const mediaContainer = document.getElementById('media-preview');
    mediaContainer.innerHTML = '';
    if (issue.image_url) {
        const urls = issue.image_url.split(',');
        urls.forEach(url => {
            if (!url) return;
            const cleanUrl = url.trim();
            const fileExt = cleanUrl.split('.').pop().split('?')[0].toLowerCase();
            const isVideo = ['mp4', 'mov', 'avi'].includes(fileExt);
            
            if (isVideo) {
                const video = document.createElement('video');
                video.src = cleanUrl;
                video.controls = true;
                video.style.width = '100%';
                video.style.maxHeight = '200px';
                video.style.borderRadius = '12px';
                video.style.border = '1px solid var(--border-color)';
                video.style.marginBottom = '0.5rem';
                mediaContainer.appendChild(video);
            } else {
                const img = document.createElement('img');
                img.src = cleanUrl;
                img.style.width = '100%';
                img.style.maxHeight = '200px';
                img.style.objectFit = 'cover';
                img.style.borderRadius = '12px';
                img.style.border = '1px solid var(--border-color)';
                img.style.marginBottom = '0.5rem';
                mediaContainer.appendChild(img);
            }
        });
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

// Search location using OpenStreetMap Nominatim API (100% free geocoding)
function searchLocation() {
    const input = document.getElementById('search-input');
    const query = input.value.trim();
    if (!query) return;

    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data && data.length > 0) {
                const lat = parseFloat(data[0].lat);
                const lon = parseFloat(data[0].lon);
                map.setView([lat, lon], 14);
            } else {
                alert('Location not found. Please try a different search.');
            }
        })
        .catch(err => {
            console.error('Search error:', err);
            alert('Could not search location. Please try again.');
        });
}

// Pan map back to user's tracked current location
function locateUser() {
    if (currentUserLocation) {
        map.setView(currentUserLocation, 16);
    } else {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition((position) => {
                const userLat = position.coords.latitude;
                const userLng = position.coords.longitude;
                currentUserLocation = [userLat, userLng];
                map.setView(currentUserLocation, 16);
            }, (err) => {
                alert("Could not retrieve current position. Check your browser location permissions.");
            });
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    }
}
