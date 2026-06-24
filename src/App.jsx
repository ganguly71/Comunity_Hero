import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  MapPin, 
  Upload, 
  CheckCircle, 
  Clock, 
  MessageSquare, 
  ThumbsUp, 
  User, 
  Shield, 
  Building, 
  Award, 
  TrendingUp, 
  PlusCircle, 
  Map, 
  ListFilter, 
  Bell, 
  ChevronRight, 
  Camera, 
  AlertOctagon, 
  Search, 
  Calendar,
  Layers,
  ArrowRight,
  Sparkles,
  Smile
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import confetti from 'canvas-confetti';
import { 
  getDB, 
  saveDB, 
  awardXP, 
  calculatePriorityScore, 
  simulateAIAnalysis, 
  checkDuplicate,
  INITIAL_ISSUES
} from './utils/mockData';

// Custom Map-Marker icons
const createCustomIcon = (severity, status) => {
  let color = '#3b82f6'; // blue
  if (status === 'resolved') {
    color = '#10b981'; // emerald
  } else {
    switch (severity) {
      case 'critical': color = '#f43f5e'; break; // rose
      case 'high': color = '#f59e0b'; break; // amber
      case 'medium': color = '#06b6d4'; break; // cyan
      default: color = '#6b7280'; // grey
    }
  }

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div class="pulse-marker pulse-marker-${status === 'resolved' ? 'resolved' : severity}" style="background-color: ${color}"></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
};

// Map click listener helper component
function MapEvents({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Map recentering helper component
function RecenterMap({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom]);
  return null;
}

export default function App() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
  const [isUsingLiveAPI, setIsUsingLiveAPI] = useState(false);

  // Global State
  const [db, setDb] = useState(getDB());
  const [activeUser, setActiveUser] = useState(db.users[0]); // Default to Aditya Kumar (Citizen)
  const [currentPage, setCurrentPage] = useState('landing'); // landing, map, report, dashboard, authority, leaderboard
  const [selectedIssueId, setSelectedIssueId] = useState(null); // Detail drawer issue
  const [notifications, setNotifications] = useState([]);
  const [toastBadge, setToastBadge] = useState(null);
  
  // Filtering states for Map
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterWard, setFilterWard] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Map viewport states
  const [mapCenter, setMapCenter] = useState([12.9716, 77.5946]);
  const [mapZoom, setMapZoom] = useState(13);

  // Center coordinate mapping for Wards
  const handleWardChange = (wardId) => {
    setFilterWard(wardId);
    
    const wardCenters = {
      w1: [12.9784, 77.6408], // Indiranagar central report
      w2: [12.9352, 77.6245], // Koramangala central report
      w3: [12.9116, 77.6388], // HSR Layout central report
      w4: [12.9698, 77.7500]  // Whitefield central report
    };
    
    if (wardId && wardCenters[wardId]) {
      setMapCenter(wardCenters[wardId]);
      setMapZoom(14);
      addNotification('info', `Centering map on ${db.wards.find(w => w.id === wardId)?.name || 'selected ward'}`);
    } else {
      setMapCenter([12.9716, 77.5946]);
      setMapZoom(13);
    }
  };

  // Reporting Form State
  const [reportTitle, setReportTitle] = useState('');
  const [reportDesc, setReportDesc] = useState('');
  const [reportCategory, setReportCategory] = useState('');
  const [reportSeverity, setReportSeverity] = useState('medium');
  const [reportLat, setReportLat] = useState(12.9716); // Default Bengaluru
  const [reportLng, setReportLng] = useState(77.5946);
  const [reportAddress, setReportAddress] = useState('Central District, Bengaluru, Karnataka');
  const [reportImage, setReportImage] = useState('');
  const [selectedPresetImage, setSelectedPresetImage] = useState('');
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiConfidence, setAiConfidence] = useState(null);
  const [aiTags, setAiTags] = useState([]);
  const [duplicateWarning, setDuplicateWarning] = useState(null);
  const [gpsLocating, setGpsLocating] = useState(false);

  // Authority Form State
  const [resolutionNote, setResolutionNote] = useState('');

  // Comment State
  const [newComment, setNewComment] = useState('');

  // Probe backend connection
  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'healthy') {
          setIsUsingLiveAPI(true);
          console.log("Connected to Live Flask/Supabase Backend!");
        }
      })
      .catch(err => {
        console.log("Using browser LocalStorage Mock DB (Run Flask server on port 5000 to enable real DB backend).");
      });
  }, []);

  // Sync Live DB
  const refreshLiveDB = async () => {
    try {
      const resReports = await fetch(`${API_URL}/api/reports`);
      const issuesData = await resReports.json();
      
      const resLeaderboard = await fetch(`${API_URL}/api/leaderboard`);
      const usersData = await resLeaderboard.json();
      
      let commentsData = db.comments;
      let historyData = db.statusHistory;
      
      if (selectedIssueId) {
        const resDetails = await fetch(`${API_URL}/api/reports/${selectedIssueId}/details`);
        const details = await resDetails.json();
        commentsData = details.comments;
        historyData = details.history;
      }
      
      // Update active user state from backend too
      let activeUserData = activeUser;
      if (activeUser) {
        const resUser = await fetch(`${API_URL}/api/users/${activeUser.id}`);
        if (resUser.ok) {
          activeUserData = await resUser.json();
        }
      }
      
      setDb(prev => ({
        ...prev,
        issues: Array.isArray(issuesData) ? issuesData : prev.issues,
        users: Array.isArray(usersData) ? usersData.map(u => ({
          id: u.id,
          email: u.email,
          fullName: u.full_name,
          phone: u.phone,
          avatarUrl: u.avatar_url,
          role: u.role,
          wardId: u.ward_id,
          xpPoints: u.xp_points,
          badgeIds: u.badge_ids || [],
          reportsCount: u.reports_count,
          verifiedCount: u.verified_count,
          createdAt: u.created_at
        })) : prev.users,
        comments: Array.isArray(commentsData) ? commentsData.map(c => ({
          id: c.id,
          issueId: c.issue_id,
          userId: c.user_id,
          content: c.content,
          isAuthority: c.is_authority,
          createdAt: c.created_at
        })) : prev.comments,
        statusHistory: Array.isArray(historyData) ? historyData.map(h => ({
          id: h.id,
          issueId: h.issue_id,
          changedBy: h.changed_by,
          oldStatus: h.old_status,
          newStatus: h.new_status,
          note: h.note,
          createdAt: h.created_at
        })) : prev.statusHistory
      }));
      
      if (activeUserData) {
        setActiveUser({
          id: activeUserData.id,
          email: activeUserData.email,
          fullName: activeUserData.full_name,
          phone: activeUserData.phone,
          avatarUrl: activeUserData.avatar_url,
          role: activeUserData.role,
          wardId: activeUserData.ward_id,
          xpPoints: activeUserData.xp_points,
          badgeIds: activeUserData.badge_ids || [],
          reportsCount: activeUserData.reports_count,
          verifiedCount: activeUserData.verified_count,
          createdAt: activeUserData.created_at
        });
      }
    } catch (e) {
      console.error("Failed to sync with live backend", e);
    }
  };

  useEffect(() => {
    if (isUsingLiveAPI) {
      refreshLiveDB();
    }
  }, [isUsingLiveAPI, selectedIssueId]);

  // Synchronize db updates to localStorage (Only if mock is active)
  useEffect(() => {
    if (!isUsingLiveAPI) {
      saveDB(db);
      const updatedUser = db.users.find(u => u.id === activeUser.id);
      if (updatedUser) {
        setActiveUser(updatedUser);
      }
    }
  }, [db, isUsingLiveAPI]);

  // Initial Seed Notification
  useEffect(() => {
    setNotifications([
      { id: 1, type: 'info', message: 'Welcome back Hero! Keep reporting to protect your neighborhood.', isRead: false, createdAt: new Date() },
      { id: 2, type: 'alert', message: 'A critical waste accumulation report was submitted in HSR Layout.', isRead: false, createdAt: new Date(Date.now() - 3600000) }
    ]);
  }, []);

  // Handle active user switching (Role simulation)
  const handleUserSwitch = (userId) => {
    const user = db.users.find(u => u.id === userId);
    if (user) {
      setActiveUser(user);
      // Redirect based on role if needed
      if (user.role === 'authority') {
        setCurrentPage('authority');
      } else {
        setCurrentPage('dashboard');
      }
      addNotification('info', `Switched view to ${user.fullName} (${user.role.toUpperCase()})`);
    }
  };

  const addNotification = (type, message, issueId = null) => {
    const newNotif = {
      id: Date.now(),
      type,
      message,
      issueId,
      isRead: false,
      createdAt: new Date()
    };
    setNotifications(prev => [newNotif, ...prev]);
  };

  // Upvote/Verification logic
  const handleVerify = async (issueId) => {
    // Check if already verified
    const alreadyVerified = db.verifications.some(v => v.issueId === issueId && v.userId === activeUser.id);
    if (alreadyVerified) {
      addNotification('alert', 'You have already verified this issue.');
      return;
    }

    if (isUsingLiveAPI) {
      try {
        const response = await fetch(`${API_URL}/api/reports/${issueId}/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId: activeUser.id })
        });
        if (response.ok) {
          triggerConfetti();
          addNotification('info', `You upvoted and verified this report (+5 XP earned)`);
          await refreshLiveDB();
        } else {
          const errData = await response.json();
          addNotification('alert', errData.error || 'Failed to verify issue');
        }
      } catch (err) {
        console.error(err);
        addNotification('alert', 'Network error connecting to backend.');
      }
      return;
    }

    // Add verification entry
    const newVerification = {
      id: `v-${Date.now()}`,
      issueId,
      userId: activeUser.id,
      type: 'upvote',
      createdAt: new Date().toISOString()
    };

    let updatedIssues = db.issues.map(issue => {
      if (issue.id === issueId) {
        // Change status to 'verified' if upvotes hit threshold (e.g. 5) and status is reported
        let newStatus = issue.status;
        if (issue.status === 'reported' && issue.upvoteCount + 1 >= 5) {
          newStatus = 'verified';
          addNotification('info', `Issue "${issue.title}" is now Community Verified!`, issueId);
        }
        return {
          ...issue,
          upvoteCount: issue.upvoteCount + 1,
          status: newStatus
        };
      }
      return issue;
    });

    let updatedDB = {
      ...db,
      verifications: [...db.verifications, newVerification],
      issues: updatedIssues
    };

    // Award XP to active user
    const oldBadgeCount = activeUser.badgeIds.length;
    updatedDB = awardXP(activeUser.id, 'verify_report', updatedDB);
    setDb(updatedDB);
    
    // Check if new badges unlocked
    const newActiveUser = updatedDB.users.find(u => u.id === activeUser.id);
    if (newActiveUser.badgeIds.length > oldBadgeCount) {
      const newlyEarned = newActiveUser.badgeIds.find(b => !activeUser.badgeIds.includes(b));
      const badgeObj = db.badges.find(b => b.id === newlyEarned);
      if (badgeObj) {
        triggerConfetti();
        setToastBadge(badgeObj);
        setTimeout(() => setToastBadge(null), 5000);
      }
    }

    addNotification('info', `You upvoted and verified this report (+5 XP earned)`);
  };

  // Add Comment
  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    if (isUsingLiveAPI) {
      try {
        const response = await fetch(`${API_URL}/api/reports/${selectedIssueId}/comments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId: activeUser.id, content: newComment })
        });
        if (response.ok) {
          setNewComment('');
          addNotification('info', 'Comment added (+2 XP earned)');
          await refreshLiveDB();
        }
      } catch (err) {
        console.error(err);
      }
      return;
    }

    const comment = {
      id: `c-${Date.now()}`,
      issueId: selectedIssueId,
      userId: activeUser.id,
      content: newComment,
      isAuthority: activeUser.role === 'authority',
      createdAt: new Date().toISOString()
    };

    let updatedDB = {
      ...db,
      comments: [...db.comments, comment]
    };

    // Award XP for contributing to discussion (+2 XP)
    updatedDB = awardXP(activeUser.id, 'comment', updatedDB);
    setDb(updatedDB);
    setNewComment('');
    addNotification('info', 'Comment added (+2 XP earned)');
  };

  // Simulated AI Analyzer
  const handleAIScan = async () => {
    if (!reportDesc && !selectedPresetImage) {
      alert("Please enter a description or select an image to scan.");
      return;
    }
    setAiAnalyzing(true);

    if (isUsingLiveAPI) {
      try {
        const response = await fetch(`${API_URL}/api/reports/ai-scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description: reportDesc })
        });
        if (response.ok) {
          const results = await response.json();
          setReportCategory(results.category);
          setReportSeverity(results.severity);
          setReportTitle(results.suggestedTitle);
          setAiConfidence(results.confidence);
          setAiTags(results.tags);
          setAiAnalyzing(false);

          // Check duplicates via live reports list
          const res = await fetch(`${API_URL}/api/reports?category=${results.category}`);
          const activeIssues = res.ok ? await res.json() : [];
          const dup = checkDuplicate(reportLat, reportLng, results.category, activeIssues);
          if (dup) {
            setDuplicateWarning(dup);
          } else {
            setDuplicateWarning(null);
          }
        }
      } catch (err) {
        console.error(err);
        setAiAnalyzing(false);
      }
      return;
    }

    setTimeout(() => {
      const results = simulateAIAnalysis(selectedPresetImage || 'custom', reportDesc);
      setReportCategory(results.category);
      setReportSeverity(results.severity);
      setReportTitle(results.suggestedTitle);
      setAiConfidence(results.confidence);
      setAiTags(results.tags);
      setAiAnalyzing(false);

      // Check duplicates
      const dup = checkDuplicate(reportLat, reportLng, results.category, db.issues);
      if (dup) {
        setDuplicateWarning(dup);
      } else {
        setDuplicateWarning(null);
      }
    }, 1500);
  };

  // GPS Simulation
  const handleGPSCapture = () => {
    setGpsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        // Offset slightly to place in Bangalore for our mock environment
        // Bangalore range: 12.9 - 13.0, 77.5 - 77.7
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        
        // If coordinate is in India/Bangalore range, use it directly. Otherwise map to Bangalore center
        const isInBangalore = lat > 12.0 && lat < 13.5 && lng > 77.0 && lng < 78.5;
        const finalLat = isInBangalore ? lat : 12.9716 + (Math.random() - 0.5) * 0.05;
        const finalLng = isInBangalore ? lng : 77.5946 + (Math.random() - 0.5) * 0.05;
        
        setReportLat(finalLat);
        setReportLng(finalLng);
        setReportAddress(`Gps captured near Sector 4, Outer Ring Road, Bengaluru`);
        setGpsLocating(false);
        addNotification('info', 'GPS coordinates successfully captured.');
      },
      (error) => {
        // Fallback simulation
        const fakeLat = 12.9716 + (Math.random() - 0.5) * 0.03;
        const fakeLng = 77.5946 + (Math.random() - 0.5) * 0.03;
        setReportLat(fakeLat);
        setReportLng(fakeLng);
        setReportAddress(`Simulated GPS Pin: Ward 3, Indiranagar, Bengaluru`);
        setGpsLocating(false);
        addNotification('info', 'Simulated GPS Pin drop successfully created.');
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  };

  // Submit Issue
  const handleReportSubmit = async (e) => {
    e.preventDefault();
    if (!reportTitle || !reportCategory) {
      alert("Title and Category are required! Run AI Scan first to auto-populate.");
      return;
    }

    if (isUsingLiveAPI) {
      try {
        const response = await fetch(`${API_URL}/api/reports`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: reportTitle,
            description: reportDesc,
            category: reportCategory,
            severity: reportSeverity,
            latitude: reportLat,
            longitude: reportLng,
            addressText: reportAddress,
            mediaUrl: selectedPresetImage,
            reporterId: activeUser.id
          })
        });
        if (response.ok) {
          const resData = await response.json();
          triggerConfetti();
          addNotification('info', `Report "${reportTitle}" successfully submitted! (+10 XP earned)`);
          
          // Reset Form
          setReportTitle('');
          setReportDesc('');
          setReportCategory('');
          setReportSeverity('medium');
          setReportImage('');
          setSelectedPresetImage('');
          setAiConfidence(null);
          setAiTags([]);
          setDuplicateWarning(null);

          // Redirect
          setCurrentPage('map');
          setSelectedIssueId(resData.id);
          await refreshLiveDB();
        }
      } catch (err) {
        console.error(err);
      }
      return;
    }

    const newIssue = {
      id: `iss-${Date.now()}`,
      title: reportTitle,
      description: reportDesc || `No description provided. AI classified image.`,
      category: reportCategory,
      severity: reportSeverity,
      status: 'reported',
      mediaUrls: [selectedPresetImage || 'https://images.unsplash.com/photo-1599740831464-54c478627ec3?auto=format&fit=crop&w=800&q=80'],
      latitude: reportLat,
      longitude: reportLng,
      addressText: reportAddress,
      wardId: 'w1', // Assign to Indiranagar default
      reporterId: activeUser.id,
      assignedTo: null,
      aiCategory: reportCategory,
      aiConfidence: aiConfidence || 0.90,
      upvoteCount: 0,
      isDuplicate: duplicateWarning ? true : false,
      duplicateOf: duplicateWarning ? duplicateWarning.id : null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      resolvedAt: null
    };

    const statusHistoryLog = {
      id: `sh-${Date.now()}`,
      issueId: newIssue.id,
      changedBy: activeUser.id,
      oldStatus: null,
      newStatus: 'reported',
      note: 'Initial citizen submission verified by on-device AI.',
      createdAt: new Date().toISOString()
    };

    let updatedDB = {
      ...db,
      issues: [newIssue, ...db.issues],
      statusHistory: [...db.statusHistory, statusHistoryLog]
    };

    // Award XP (+10 XP)
    const oldBadgeCount = activeUser.badgeIds.length;
    updatedDB = awardXP(activeUser.id, 'submit_report', updatedDB);
    
    // Check badges
    const newActiveUser = updatedDB.users.find(u => u.id === activeUser.id);
    setDb(updatedDB);

    // Confetti!
    triggerConfetti();
    
    if (newActiveUser.badgeIds.length > oldBadgeCount) {
      const newlyEarned = newActiveUser.badgeIds.find(b => !activeUser.badgeIds.includes(b));
      const badgeObj = db.badges.find(b => b.id === newlyEarned);
      if (badgeObj) {
        setToastBadge(badgeObj);
        setTimeout(() => setToastBadge(null), 5000);
      }
    }

    addNotification('info', `Report "${reportTitle}" successfully submitted! (+10 XP earned)`);
    
    // Reset Form
    setReportTitle('');
    setReportDesc('');
    setReportCategory('');
    setReportSeverity('medium');
    setReportImage('');
    setSelectedPresetImage('');
    setAiConfidence(null);
    setAiTags([]);
    setDuplicateWarning(null);

    // Redirect
    setCurrentPage('map');
    setSelectedIssueId(newIssue.id);
  };

  // Authority actions: status advance
  const handleUpdateStatus = async (issueId, newStatus) => {
    if (!resolutionNote.trim()) {
      alert("Please add a brief update or resolution note.");
      return;
    }

    if (isUsingLiveAPI) {
      try {
        const response = await fetch(`${API_URL}/api/reports/${issueId}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus, changedBy: activeUser.id, note: resolutionNote })
        });
        if (response.ok) {
          if (newStatus === 'resolved') {
            addNotification('info', `Issue marked as RESOLVED! Reporter awarded +50 XP.`, issueId);
          } else {
            addNotification('info', `Issue status updated to ${newStatus.toUpperCase()}`, issueId);
          }
          setResolutionNote('');
          await refreshLiveDB();
        }
      } catch (err) {
        console.error(err);
      }
      return;
    }

    const issue = db.issues.find(iss => iss.id === issueId);
    if (!issue) return;

    const oldStatus = issue.status;
    const historyLog = {
      id: `sh-${Date.now()}`,
      issueId,
      changedBy: activeUser.id,
      oldStatus,
      newStatus,
      note: resolutionNote,
      createdAt: new Date().toISOString()
    };

    let updatedIssues = db.issues.map(iss => {
      if (iss.id === issueId) {
        return {
          ...iss,
          status: newStatus,
          resolvedAt: newStatus === 'resolved' ? new Date().toISOString() : iss.resolvedAt,
          updatedAt: new Date().toISOString()
        };
      }
      return iss;
    });

    let updatedDB = {
      ...db,
      issues: updatedIssues,
      statusHistory: [...db.statusHistory, historyLog]
    };

    // If resolved, award the reporter 50 XP
    if (newStatus === 'resolved') {
      updatedDB = awardXP(issue.reporterId, 'report_resolved', updatedDB);
      addNotification('info', `Issue "${issue.title}" marked as RESOLVED! Reporter awarded +50 XP.`, issueId);
    } else {
      addNotification('info', `Issue status updated to ${newStatus.toUpperCase()}`, issueId);
    }

    setDb(updatedDB);
    setResolutionNote('');
  };

  // Confetti trigger
  const triggerConfetti = () => {
    confetti({
      particleCount: 120,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b']
    });
  };

  // Filters logic
  const filteredIssues = db.issues.filter(issue => {
    const categoryMatch = filterCategory === 'all' || issue.category === filterCategory;
    const severityMatch = filterSeverity === 'all' || issue.severity === filterSeverity;
    const statusMatch = filterStatus === 'all' || issue.status === filterStatus;
    const wardMatch = filterWard === 'all' || issue.wardId === filterWard;
    const searchMatch = !searchQuery || 
      issue.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      issue.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      issue.addressText.toLowerCase().includes(searchQuery.toLowerCase());
    return categoryMatch && severityMatch && statusMatch && searchMatch && wardMatch;
  });

  const selectedIssue = db.issues.find(iss => iss.id === selectedIssueId);

  // Statistics summaries
  const totalIssuesCount = db.issues.length;
  const resolvedIssuesCount = db.issues.filter(i => i.status === 'resolved').length;
  const inProgressIssuesCount = db.issues.filter(i => i.status === 'in_progress').length;
  const totalUpvotes = db.issues.reduce((sum, i) => sum + i.upvoteCount, 0);

  // Preset images for reporting simulation
  const PRESET_IMAGES = [
    { label: "Pothole", url: "https://images.unsplash.com/photo-1515162305285-0293e4767cc2?auto=format&fit=crop&w=300&q=80", type: "pothole", desc: "Large deep pothole on main road section causing issues." },
    { label: "Streetlight", url: "https://images.unsplash.com/photo-1509024644558-2f56ce76c490?auto=format&fit=crop&w=300&q=80", type: "streetlight", desc: "Streetlight bulb broken, road dark." },
    { label: "Water Leak", url: "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=300&q=80", type: "water_leak", desc: "Water supply pipe pipe crack spraying water onto the path." },
    { label: "Waste", url: "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=300&q=80", type: "waste", desc: "Huge waste dumpster overflowing with plastics and garbage." }
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Background ambient animations */}
      <div className="bg-ambient-glow"></div>

      {/* Top Banner simulation switch */}
      <div className="role-switcher-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'rgba(255,255,255,0.6)', fontWeight: '500' }}>🔬 Judge Simulator Console:</span>
          <select 
            value={activeUser.id} 
            onChange={(e) => handleUserSwitch(e.target.value)}
            style={{
              background: 'rgba(20, 24, 39, 0.9)',
              border: '1px solid hsl(var(--primary) / 0.5)',
              color: 'white',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '0.8rem',
              cursor: 'pointer'
            }}
          >
            {db.users.map(u => (
              <option key={u.id} value={u.id}>
                {u.fullName} ({u.role.toUpperCase()})
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.8rem', color: '#a78bfa', fontWeight: 'bold' }}>
            Current Level: {Math.floor(activeUser.xpPoints / 100) + 1}
          </span>
          <span style={{ fontSize: '0.8rem', color: '#22d3ee', fontWeight: 'bold' }}>
            XP Points: {activeUser.xpPoints}
          </span>
        </div>
      </div>

      {/* Header bar */}
      <header style={{
        background: 'rgba(10, 14, 25, 0.75)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-light)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        padding: '12px 24px'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          {/* Logo */}
          <div 
            onClick={() => setCurrentPage('landing')} 
            style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}
          >
            <div style={{
              background: 'linear-gradient(135deg, hsl(var(--primary)), #a78bfa)',
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(139, 92, 246, 0.3)'
            }}>
              <span style={{ fontSize: '1.4rem' }}>🦸‍♂️</span>
            </div>
            <div>
              <h1 style={{ fontSize: '1.25rem', color: 'white', lineHeight: 1 }}>Community Hero</h1>
              <span style={{ fontSize: '0.7rem', color: 'hsl(var(--cyan))', letterSpacing: '0.05em', fontWeight: 'bold' }}>
                HYPERLOCAL SOLVER
              </span>
            </div>
          </div>

          {/* Navigation */}
          <nav style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <button 
              onClick={() => setCurrentPage('map')} 
              style={{
                border: 'none',
                color: currentPage === 'map' ? 'hsl(var(--primary-hover))' : 'hsl(var(--text-secondary))',
                fontSize: '0.9rem',
                fontWeight: '550',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                background: currentPage === 'map' ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                transition: 'all 0.2s'
              }}
            >
              <Map size={16} />
              Interactive Map
            </button>
            <button 
              onClick={() => setCurrentPage('report')} 
              style={{
                border: 'none',
                color: currentPage === 'report' ? 'hsl(var(--primary-hover))' : 'hsl(var(--text-secondary))',
                fontSize: '0.9rem',
                fontWeight: '550',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                background: currentPage === 'report' ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                transition: 'all 0.2s'
              }}
            >
              <PlusCircle size={16} />
              Report Issue
            </button>
            <button 
              onClick={() => setCurrentPage('leaderboard')} 
              style={{
                border: 'none',
                color: currentPage === 'leaderboard' ? 'hsl(var(--primary-hover))' : 'hsl(var(--text-secondary))',
                fontSize: '0.9rem',
                fontWeight: '550',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                background: currentPage === 'leaderboard' ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                transition: 'all 0.2s'
              }}
            >
              <Award size={16} />
              Leaderboard
            </button>
            {activeUser.role === 'authority' ? (
              <button 
                onClick={() => setCurrentPage('authority')} 
                style={{
                  border: 'none',
                  color: currentPage === 'authority' ? 'hsl(var(--primary-hover))' : 'hsl(var(--text-secondary))',
                  fontSize: '0.9rem',
                  fontWeight: '550',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '8px',
                  background: currentPage === 'authority' ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                  transition: 'all 0.2s'
                }}
              >
                <Shield size={16} />
                Gov Dashboard
              </button>
            ) : (
              <button 
                onClick={() => setCurrentPage('dashboard')} 
                style={{
                  border: 'none',
                  color: currentPage === 'dashboard' ? 'hsl(var(--primary-hover))' : 'hsl(var(--text-secondary))',
                  fontSize: '0.9rem',
                  fontWeight: '550',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '8px',
                  background: currentPage === 'dashboard' ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                  transition: 'all 0.2s'
                }}
              >
                <User size={16} />
                My Profile
              </button>
            )}
          </nav>

          {/* User profile bubble */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ position: 'relative', cursor: 'pointer' }}>
              <div style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-light)',
                borderRadius: '8px',
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Bell size={18} style={{ color: 'hsl(var(--text-secondary))' }} />
                {notifications.some(n => !n.isRead) && (
                  <span style={{
                    position: 'absolute',
                    top: '2px',
                    right: '2px',
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: 'hsl(var(--rose))'
                  }}></span>
                )}
              </div>
            </div>
            <div 
              onClick={() => setCurrentPage(activeUser.role === 'authority' ? 'authority' : 'dashboard')}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
            >
              <img 
                src={activeUser.avatarUrl} 
                alt={activeUser.fullName}
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  border: '1px solid hsl(var(--primary) / 0.5)'
                }}
              />
              <div style={{ display: 'none', md: 'block' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: '500', color: 'white', display: 'block' }}>
                  {activeUser.fullName.split(' ')[0]}
                </span>
                <span style={{ fontSize: '0.65rem', color: 'hsl(var(--text-muted))', display: 'block' }}>
                  {activeUser.role.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>

        {/* 1. LANDING PAGE */}
        {currentPage === 'landing' && (
          <div className="animate-fade-in" style={{ padding: '20px 0' }}>
            {/* Hero Section */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              gap: '24px',
              padding: '60px 0 40px 0'
            }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(139, 92, 246, 0.1)',
                border: '1px solid rgba(139, 92, 246, 0.25)',
                padding: '6px 14px',
                borderRadius: '99px',
                color: '#a78bfa',
                fontSize: '0.85rem',
                fontWeight: '600'
              }}>
                <Sparkles size={14} />
                Empowering Local Communities via AI
              </div>
              <h1 style={{
                fontSize: '3.5rem',
                lineHeight: 1.1,
                maxWidth: '800px',
                background: 'linear-gradient(to right, #ffffff, #a78bfa, #22d3ee)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: 800
              }}>
                Be a Hero. Fix Your Neighborhood.
              </h1>
              <p style={{
                color: 'hsl(var(--text-secondary))',
                fontSize: '1.15rem',
                maxWidth: '600px',
                lineHeight: 1.6
              }}>
                Report infrastructure issues, upvote neighbors' reports, earn gamified XP points, and collaborate directly with local authorities to resolve them.
              </p>
              
              <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
                <button 
                  onClick={() => setCurrentPage('report')}
                  className="btn-primary" 
                  style={{ padding: '14px 28px', fontSize: '1rem' }}
                >
                  <PlusCircle size={18} />
                  Report An Issue
                </button>
                <button 
                  onClick={() => setCurrentPage('map')}
                  className="btn-secondary" 
                  style={{ padding: '14px 28px', fontSize: '1rem' }}
                >
                  <Map size={18} />
                  Browse Issue Map
                </button>
              </div>
            </div>

            {/* Dashboard metrics ticker */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '20px',
              margin: '30px 0'
            }}>
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '8px' }}>
                  ACTIVE WARD REPORTS
                </span>
                <span style={{ fontSize: '2.5rem', fontWeight: '800', color: 'white', fontFamily: 'var(--font-heading)' }}>
                  {totalIssuesCount}
                </span>
              </div>
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '8px' }}>
                  RESOLVED TO DATE
                </span>
                <span style={{ fontSize: '2.5rem', fontWeight: '800', color: 'hsl(var(--emerald))', fontFamily: 'var(--font-heading)' }}>
                  {resolvedIssuesCount}
                </span>
              </div>
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '8px' }}>
                  IN PROGRESS
                </span>
                <span style={{ fontSize: '2.5rem', fontWeight: '800', color: 'hsl(var(--amber))', fontFamily: 'var(--font-heading)' }}>
                  {inProgressIssuesCount}
                </span>
              </div>
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '8px' }}>
                  COMMUNITY ENGAGEMENT
                </span>
                <span style={{ fontSize: '2.5rem', fontWeight: '800', color: 'hsl(var(--cyan))', fontFamily: 'var(--font-heading)' }}>
                  {totalUpvotes} <span style={{ fontSize: '1rem', fontWeight: 'normal', color: 'hsl(var(--text-muted))' }}>verifications</span>
                </span>
              </div>
            </div>

            {/* How it works */}
            <div style={{ padding: '40px 0', textAlign: 'center' }}>
              <h2 style={{ fontSize: '1.75rem', marginBottom: '30px' }}>Civic Resolution Workflow</h2>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '24px',
                textAlign: 'left'
              }}>
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(139, 92, 246, 0.1)',
                    display: 'flex', alignItems: 'center', justifySelf: 'start', justifyContent: 'center', marginBottom: '16px', color: '#a78bfa'
                  }}>1</div>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Snap & Describe</h3>
                  <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', lineHeight: 1.5 }}>
                    Snap a photo of the pothole, leak, or debris. Our AI instantly processes it to suggest category, tags, and severity details.
                  </p>
                </div>
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.1)',
                    display: 'flex', alignItems: 'center', justifySelf: 'start', justifyContent: 'center', marginBottom: '16px', color: '#22d3ee'
                  }}>2</div>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Geolocate & Check</h3>
                  <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', lineHeight: 1.5 }}>
                    The system grabs your precise GPS coordinate. If someone else already reported the same issue nearby, the system flags it to avoid duplicates.
                  </p>
                </div>
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.1)',
                    display: 'flex', alignItems: 'center', justifySelf: 'start', justifyContent: 'center', marginBottom: '16px', color: '#f59e0b'
                  }}>3</div>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Community Backing</h3>
                  <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', lineHeight: 1.5 }}>
                    Neighbors see the issue on the map, mark it "I see this too" to upvote, pushing it higher on the priority score list.
                  </p>
                </div>
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.1)',
                    display: 'flex', alignItems: 'center', justifySelf: 'start', justifyContent: 'center', marginBottom: '16px', color: '#10b981'
                  }}>4</div>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Official Resolution</h3>
                  <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', lineHeight: 1.5 }}>
                    Municipal teams filter by priority score, verify details, address the issue physically, and post photo resolution proof, awarding you bonus XP!
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 2. INTERACTIVE MAP & DETAILS */}
        {currentPage === 'map' && (
          <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px', minHeight: 'calc(100vh - 160px)' }}>
            
            {/* Sidebar Filters */}
            <div className="glass-card" style={{ padding: '20px', height: 'fit-content', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '4px' }}>Filter Issues</h2>
                <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))' }}>Search and isolate specific reports</span>
              </div>

              {/* Search Bar */}
              <div style={{ position: 'relative' }}>
                <input 
                  type="text" 
                  placeholder="Search keywords..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-light)',
                    color: 'white',
                    padding: '10px 12px 10px 36px',
                    borderRadius: '8px',
                    fontSize: '0.85rem'
                  }}
                />
                <Search size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'hsl(var(--text-muted))' }} />
              </div>

              {/* Category Filter */}
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                  CATEGORY
                </label>
                <select 
                  value={filterCategory} 
                  onChange={(e) => setFilterCategory(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-light)',
                    color: 'white',
                    padding: '8px',
                    borderRadius: '8px',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="all">All Categories</option>
                  <option value="pothole">Pothole / Road Damage</option>
                  <option value="water_leak">Water Leakage</option>
                  <option value="streetlight">Broken Streetlight</option>
                  <option value="waste">Waste Dump</option>
                  <option value="road_damage">Road Damage / Erosion</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Ward / Area Filter */}
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                  SEARCH WARD / AREA
                </label>
                <select 
                  value={filterWard} 
                  onChange={(e) => handleWardChange(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-light)',
                    color: 'white',
                    padding: '8px',
                    borderRadius: '8px',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="all">All Wards / Areas</option>
                  {db.wards.map(w => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
              </div>

              {/* Severity Filter */}
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                  SEVERITY
                </label>
                <select 
                  value={filterSeverity} 
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-light)',
                    color: 'white',
                    padding: '8px',
                    borderRadius: '8px',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical Only</option>
                  <option value="high">High & Critical</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                  STATUS
                </label>
                <select 
                  value={filterStatus} 
                  onChange={(e) => setFilterStatus(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-light)',
                    color: 'white',
                    padding: '8px',
                    borderRadius: '8px',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="all">All Statuses</option>
                  <option value="reported">Reported</option>
                  <option value="verified">Verified</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>

              {/* Reset Filters */}
              <button 
                onClick={() => {
                  setFilterCategory('all');
                  setFilterSeverity('all');
                  setFilterStatus('all');
                  setFilterWard('all');
                  setSearchQuery('');
                  setMapCenter([12.9716, 77.5946]);
                  setMapZoom(13);
                }}
                className="btn-secondary" 
                style={{ width: '100%', justifyContent: 'center', fontSize: '0.85rem', padding: '8px' }}
              >
                Clear Filters
              </button>
            </div>

            {/* Main Map + Details Drawer split */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ flex: 1, position: 'relative', minHeight: '450px' }}>
                <MapContainer 
                  center={mapCenter} 
                  zoom={mapZoom} 
                  style={{ height: '100%', width: '100%', minHeight: '450px' }}
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  />
                  <RecenterMap center={mapCenter} zoom={mapZoom} />
                  {filteredIssues.map(issue => (
                    <Marker 
                      key={issue.id} 
                      position={[issue.latitude, issue.longitude]}
                      icon={createCustomIcon(issue.severity, issue.status)}
                      eventHandlers={{
                        click: () => {
                          setSelectedIssueId(issue.id);
                        }
                      }}
                    >
                      <Popup>
                        <div style={{ padding: '4px' }}>
                          <h4 style={{ color: 'white', marginBottom: '4px', fontSize: '0.9rem' }}>{issue.title}</h4>
                          <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                            <span className={`badge badge-${issue.category}`}>{issue.category}</span>
                            <span className={`badge badge-${issue.severity}`}>{issue.severity}</span>
                          </div>
                          <img 
                            src={issue.mediaUrls[0]} 
                            alt={issue.title} 
                            style={{ width: '100%', height: '80px', objectFit: 'cover', borderRadius: '4px', marginBottom: '8px' }}
                          />
                          <button 
                            onClick={() => setSelectedIssueId(issue.id)}
                            style={{
                              width: '100%',
                              background: 'hsl(var(--primary))',
                              border: 'none',
                              color: 'white',
                              borderRadius: '4px',
                              padding: '4px 0',
                              cursor: 'pointer',
                              fontSize: '0.8rem'
                            }}
                          >
                            Open Details Drawer
                          </button>
                        </div>
                      </Popup>
                    </Marker>
                  ))}
                </MapContainer>

                {/* Heatmap Layer toggle indicator */}
                <div style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  zIndex: 999,
                  background: 'rgba(10, 14, 25, 0.9)',
                  border: '1px solid var(--border-light)',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: 'white'
                }}>
                  <Layers size={14} style={{ color: 'hsl(var(--cyan))' }} />
                  <span>Map Layer: <b>Standard Streets</b> (Dark Mode Filtered)</span>
                </div>
              </div>

              {/* Selected Issue Details Panel (Drawer) */}
              {selectedIssue && (
                <div className="glass-card animate-slide-up" style={{ padding: '24px', borderLeft: '4px solid hsl(var(--primary))' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <div>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                        <span className={`badge badge-${selectedIssue.category}`}>{selectedIssue.category}</span>
                        <span className={`badge badge-${selectedIssue.severity}`}>{selectedIssue.severity}</span>
                        <span className={`badge badge-${selectedIssue.status}`}>{selectedIssue.status.replace('_', ' ')}</span>
                        {selectedIssue.isDuplicate && (
                          <span className="badge" style={{ background: 'rgba(244,63,94,0.15)', color: 'hsl(var(--rose))', border: '1px solid hsl(var(--rose)/0.3)' }}>
                            <AlertOctagon size={10} style={{ marginRight: '4px' }} />
                            DUPLICATE FLAG
                          </span>
                        )}
                      </div>
                      <h3 style={{ fontSize: '1.5rem', color: 'white', marginBottom: '4px' }}>{selectedIssue.title}</h3>
                      <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-muted))', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <MapPin size={12} /> {selectedIssue.addressText}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                      <button 
                        onClick={() => setSelectedIssueId(null)}
                        style={{ background: 'transparent', border: 'none', color: 'hsl(var(--text-muted))', cursor: 'pointer', fontSize: '1.25rem' }}
                      >
                        ✕
                      </button>
                      <div style={{
                        background: 'rgba(6,182,212,0.1)',
                        border: '1px solid rgba(6,182,212,0.2)',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        color: 'hsl(var(--cyan))',
                        fontWeight: 'bold'
                      }}>
                        Priority Score: {calculatePriorityScore(selectedIssue)}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
                    {/* Left Column Description */}
                    <div>
                      <h4 style={{ fontSize: '0.9rem', color: 'hsl(var(--text-muted))', marginBottom: '8px', textTransform: 'uppercase' }}>Description</h4>
                      <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: '16px' }}>
                        {selectedIssue.description}
                      </p>

                      <div style={{ display: 'flex', gap: '20px', fontSize: '0.8rem', color: 'hsl(var(--text-muted))' }}>
                        <div>
                          <span>Reported By:</span>
                          <strong style={{ display: 'block', color: 'white', marginTop: '2px' }}>
                            {db.users.find(u => u.id === selectedIssue.reporterId)?.fullName || 'Citizen'}
                          </strong>
                        </div>
                        <div>
                          <span>Date Submitted:</span>
                          <strong style={{ display: 'block', color: 'white', marginTop: '2px' }}>
                            {new Date(selectedIssue.createdAt).toLocaleDateString()}
                          </strong>
                        </div>
                        <div>
                          <span>AI Classification Confidence:</span>
                          <strong style={{ display: 'block', color: 'hsl(var(--cyan))', marginTop: '2px' }}>
                            {(selectedIssue.aiConfidence * 100).toFixed(0)}%
                          </strong>
                        </div>
                      </div>
                    </div>

                    {/* Right Column Photo / Timeline Preview */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <img 
                        src={selectedIssue.mediaUrls[0]} 
                        alt="Issue file preview" 
                        style={{
                          width: '100%',
                          height: '180px',
                          objectFit: 'cover',
                          borderRadius: '8px',
                          border: '1px solid var(--border-light)'
                        }}
                      />

                      {/* Upvote engagement banner */}
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: 'rgba(255,255,255,0.03)',
                        padding: '10px 14px',
                        borderRadius: '8px',
                        border: '1px solid var(--border-light)'
                      }}>
                        <span style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))' }}>
                          Verified by <b>{selectedIssue.upvoteCount}</b> citizen{selectedIssue.upvoteCount !== 1 ? 's' : ''}
                        </span>
                        
                        <button 
                          onClick={() => handleVerify(selectedIssue.id)}
                          className="btn-primary"
                          style={{
                            padding: '6px 12px',
                            fontSize: '0.8rem',
                            borderRadius: '6px'
                          }}
                        >
                          <ThumbsUp size={12} />
                          I see this too
                        </button>
                      </div>
                    </div>
                  </div>

                  <hr style={{ border: 0, borderBottom: '1px solid var(--border-light)', margin: '20px 0' }} />

                  {/* Status Timeline & comments Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
                    {/* Status History */}
                    <div>
                      <h4 style={{ fontSize: '0.95rem', color: 'white', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={16} style={{ color: 'hsl(var(--primary))' }} />
                        Status History Timeline
                      </h4>
                      
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', position: 'relative', paddingLeft: '20px' }}>
                        {/* Vertical line connector */}
                        <div style={{
                          position: 'absolute',
                          left: '6px',
                          top: '10px',
                          bottom: '10px',
                          width: '2px',
                          background: 'rgba(255,255,255,0.08)'
                        }}></div>

                        {db.statusHistory
                          .filter(h => h.issueId === selectedIssue.id)
                          .map((hist, index) => (
                            <div key={hist.id} style={{ position: 'relative' }}>
                              {/* Dot indicator */}
                              <div style={{
                                position: 'absolute',
                                left: '-19px',
                                top: '4px',
                                width: '10px',
                                height: '10px',
                                borderRadius: '50%',
                                background: index === 0 ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.3)',
                                border: '2px solid hsl(var(--bg-app))'
                              }}></div>
                              
                              <div style={{ fontSize: '0.85rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                  <strong style={{ color: 'white' }}>{hist.newStatus.toUpperCase()}</strong>
                                  <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))' }}>
                                    {new Date(hist.createdAt).toLocaleDateString()}
                                  </span>
                                </div>
                                <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.8rem', marginTop: '2px' }}>
                                  {hist.note}
                                </p>
                                <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))', display: 'block', marginTop: '2px' }}>
                                  By: {db.users.find(u => u.id === hist.changedBy)?.fullName || 'Authority'}
                                </span>
                              </div>
                            </div>
                        ))}
                      </div>
                    </div>

                    {/* Discussion Comments Thread */}
                    <div>
                      <h4 style={{ fontSize: '0.95rem', color: 'white', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <MessageSquare size={16} style={{ color: 'hsl(var(--primary))' }} />
                        Citizen Comments ({db.comments.filter(c => c.issueId === selectedIssue.id).length})
                      </h4>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '180px', overflowY: 'auto', marginBottom: '14px', paddingRight: '4px' }}>
                        {db.comments.filter(c => c.issueId === selectedIssue.id).length === 0 ? (
                          <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-muted))' }}>No comments posted yet. Add yours below.</span>
                        ) : (
                          db.comments
                            .filter(c => c.issueId === selectedIssue.id)
                            .map(comment => {
                              const user = db.users.find(u => u.id === comment.userId);
                              return (
                                <div 
                                  key={comment.id} 
                                  style={{
                                    background: comment.isAuthority ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                                    border: comment.isAuthority ? '1px solid rgba(16, 185, 129, 0.2)' : '1px solid var(--border-light)',
                                    borderRadius: '8px',
                                    padding: '10px'
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: comment.isAuthority ? 'hsl(var(--emerald))' : 'white' }}>
                                      {user?.fullName || 'Citizen'} {comment.isAuthority && '✓ (Municipal Official)'}
                                    </span>
                                    <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))' }}>
                                      {new Date(comment.createdAt).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <p style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))', lineHeight: 1.4 }}>
                                    {comment.content}
                                  </p>
                                </div>
                              );
                            })
                        )}
                      </div>

                      {/* Comment Input */}
                      <form onSubmit={handleAddComment} style={{ display: 'flex', gap: '8px' }}>
                        <input 
                          type="text" 
                          placeholder="Write a message/update..."
                          value={newComment}
                          onChange={(e) => setNewComment(e.target.value)}
                          style={{
                            flex: 1,
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-light)',
                            color: 'white',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '0.85rem'
                          }}
                        />
                        <button 
                          type="submit" 
                          className="btn-primary" 
                          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                        >
                          Send
                        </button>
                      </form>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 3. REPORT AN ISSUE FORM */}
        {currentPage === 'report' && (
          <div className="animate-fade-in" style={{ maxWidth: '750px', margin: '0 auto' }}>
            <div className="glass-card" style={{ padding: '30px' }}>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
                <div style={{
                  background: 'rgba(139, 92, 246, 0.1)',
                  borderRadius: '10px',
                  width: '42px',
                  height: '42px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#a78bfa'
                }}>
                  <Camera size={20} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.5rem', color: 'white' }}>Report New Local Problem</h2>
                  <p style={{ fontSize: '0.8rem', color: 'hsl(var(--text-muted))' }}>AI analyzes your submission instantly to auto-fill ward metadata.</p>
                </div>
              </div>

              <form onSubmit={handleReportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* Geolocation selector */}
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                    1. CAPTURE GEOLOCATION
                  </label>
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                    <button 
                      type="button" 
                      onClick={handleGPSCapture}
                      className="btn-secondary"
                      style={{ fontSize: '0.85rem', flex: 1, justifyContent: 'center' }}
                    >
                      <MapPin size={16} />
                      {gpsLocating ? 'Acquiring GPS Signal...' : 'Acquire Current GPS Location'}
                    </button>
                  </div>
                  
                  {/* Address Display / Edit */}
                  <input 
                    type="text" 
                    value={reportAddress}
                    onChange={(e) => setReportAddress(e.target.value)}
                    placeholder="Physical landmark or address..."
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-light)',
                      color: 'white',
                      padding: '10px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      marginBottom: '8px'
                    }}
                  />
                  
                  {/* Miniature Pin Drop Map */}
                  <div style={{ height: '180px', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-light)' }}>
                    <MapContainer 
                      center={[reportLat, reportLng]} 
                      zoom={15} 
                      style={{ height: '100%', width: '100%' }}
                    >
                      <TileLayer
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        attribution='&copy; OpenStreetMap'
                      />
                      <Marker position={[reportLat, reportLng]} icon={createCustomIcon('medium', 'reported')} />
                      <MapEvents onMapClick={(lat, lng) => {
                        setReportLat(lat);
                        setReportLng(lng);
                        setReportAddress(`Manual pin drop coordinates: [${lat.toFixed(5)}, ${lng.toFixed(5)}]`);
                      }} />
                    </MapContainer>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))', display: 'block', marginTop: '6px' }}>
                    💡 Tap on the map inside the box to fine-tune the report pin location manually.
                  </span>
                </div>

                {/* Preset image picker simulation */}
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                    2. UPLOAD MEDIA / SELECT PRESET FOR SIMULATION
                  </label>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '12px' }}>
                    {PRESET_IMAGES.map((preset, idx) => (
                      <div 
                        key={idx}
                        onClick={() => {
                          setSelectedPresetImage(preset.url);
                          setReportDesc(preset.desc);
                          addNotification('info', `Simulating ${preset.label} image upload.`);
                        }}
                        style={{
                          cursor: 'pointer',
                          borderRadius: '8px',
                          overflow: 'hidden',
                          border: selectedPresetImage === preset.url ? '2px solid hsl(var(--primary))' : '2px solid transparent',
                          opacity: selectedPresetImage === preset.url ? 1 : 0.6,
                          transition: 'all 0.2s',
                          position: 'relative'
                        }}
                      >
                        <img src={preset.url} alt={preset.label} style={{ width: '100%', height: '70px', objectFit: 'cover' }} />
                        <div style={{
                          position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(0,0,0,0.7)',
                          textAlign: 'center', fontSize: '0.65rem', color: 'white', padding: '2px 0'
                        }}>
                          {preset.label}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Description input */}
                  <label style={{ fontSize: '0.85rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '8px' }}>
                    3. PROBLEM DESCRIPTION
                  </label>
                  <textarea 
                    value={reportDesc}
                    onChange={(e) => setReportDesc(e.target.value)}
                    placeholder="Describe the issue. (e.g. Broken pothole causing bikes to crash near the turn. Water is pooling.)"
                    rows="3"
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-light)',
                      color: 'white',
                      padding: '10px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      resize: 'vertical'
                    }}
                  ></textarea>
                </div>

                {/* AI Tagger Actions */}
                <div style={{
                  background: 'rgba(139, 92, 246, 0.05)',
                  border: '1px solid rgba(139, 92, 246, 0.15)',
                  padding: '16px',
                  borderRadius: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Sparkles size={16} style={{ color: '#a78bfa' }} />
                      <strong style={{ fontSize: '0.85rem', color: 'white' }}>On-Device Gemini AI Analyzer</strong>
                    </div>
                    <button 
                      type="button" 
                      onClick={handleAIScan}
                      disabled={aiAnalyzing}
                      className="btn-primary"
                      style={{ padding: '6px 14px', fontSize: '0.8rem', background: 'linear-gradient(135deg, #06b6d4, #8b5cf6)' }}
                    >
                      {aiAnalyzing ? 'Analyzing Submission...' : 'Trigger AI Auto-Fill Scan'}
                    </button>
                  </div>

                  {aiConfidence ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                        <span style={{ color: 'hsl(var(--text-muted))' }}>AI Confidence: <b>{(aiConfidence*100).toFixed(0)}%</b></span>
                        <span style={{ color: '#22d3ee' }}>Scan Status: Successful ✔</span>
                      </div>
                      
                      {/* Suggested Title Input */}
                      <div>
                        <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-secondary))' }}>Suggested Title:</span>
                        <input 
                          type="text" 
                          value={reportTitle}
                          onChange={(e) => setReportTitle(e.target.value)}
                          style={{
                            width: '100%',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-light)',
                            color: 'white',
                            padding: '6px 10px',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            marginTop: '2px'
                          }}
                        />
                      </div>

                      {/* Tag list suggestions */}
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {aiTags.map((tag, idx) => (
                          <span key={idx} style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-light)', color: 'hsl(var(--text-secondary))', fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px' }}>
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))' }}>
                      Click scan to dynamically generate category tags, suggested title, severity, and verify proximity duplicates.
                    </span>
                  )}
                </div>

                {/* Form fields populated by user/AI */}
                {aiConfidence && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }} className="animate-fade-in">
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '6px' }}>
                        CHOSEN CATEGORY
                      </label>
                      <select 
                        value={reportCategory}
                        onChange={(e) => setReportCategory(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'rgba(255,255,255,0.05)',
                          border: '1px solid var(--border-light)',
                          color: 'white',
                          padding: '8px',
                          borderRadius: '8px',
                          fontSize: '0.85rem'
                        }}
                      >
                        <option value="">Select...</option>
                        <option value="pothole">Pothole</option>
                        <option value="water_leak">Water Leakage</option>
                        <option value="streetlight">Broken Streetlight</option>
                        <option value="waste">Waste Dump</option>
                        <option value="road_damage">Road Damage</option>
                        <option value="other">Other</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', display: 'block', marginBottom: '6px' }}>
                        SEVERITY LEVEL
                      </label>
                      <select 
                        value={reportSeverity}
                        onChange={(e) => setReportSeverity(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'rgba(255,255,255,0.05)',
                          border: '1px solid var(--border-light)',
                          color: 'white',
                          padding: '8px',
                          borderRadius: '8px',
                          fontSize: '0.85rem'
                        }}
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>
                  </div>
                )}

                {/* Duplicate detected warning notification */}
                {duplicateWarning && (
                  <div style={{
                    background: 'rgba(244,63,94,0.1)',
                    border: '1px solid rgba(244,63,94,0.2)',
                    padding: '14px',
                    borderRadius: '8px',
                    color: 'hsl(var(--rose))',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }} className="animate-fade-in">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 'bold' }}>
                      <AlertTriangle size={16} /> Possible Duplicate Detected Nearby!
                    </span>
                    <p style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))' }}>
                      An unresolved "{duplicateWarning.category}" issue titled <b>"{duplicateWarning.title}"</b> exists within 150m.
                    </p>
                    <button 
                      type="button"
                      onClick={() => {
                        setSelectedIssueId(duplicateWarning.id);
                        setCurrentPage('map');
                      }}
                      style={{
                        alignSelf: 'flex-start',
                        background: 'transparent',
                        border: 'underline',
                        color: 'hsl(var(--rose))',
                        fontWeight: 'bold',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        padding: 0
                      }}
                    >
                      View the active report instead →
                    </button>
                  </div>
                )}

                {/* Action buttons */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '10px' }}>
                  <button 
                    type="button" 
                    onClick={() => setCurrentPage('map')}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    className="btn-primary"
                  >
                    <CheckCircle size={16} />
                    Confirm & Submit Report
                  </button>
                </div>

              </form>
            </div>
          </div>
        )}

        {/* 4. CITIZEN DASHBOARD */}
        {currentPage === 'dashboard' && (
          <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
            
            {/* Left Column profile metrics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                <img 
                  src={activeUser.avatarUrl} 
                  alt={activeUser.fullName} 
                  style={{
                    width: '90px',
                    height: '90px',
                    borderRadius: '50%',
                    border: '3px solid hsl(var(--primary))',
                    marginBottom: '14px',
                    boxShadow: '0 0 16px var(--primary-glow)'
                  }}
                />
                <h3 style={{ fontSize: '1.35rem', color: 'white', marginBottom: '2px' }}>{activeUser.fullName}</h3>
                <span style={{
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  background: 'rgba(139, 92, 246, 0.15)',
                  color: '#a78bfa',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontWeight: 'bold'
                }}>
                  Level {Math.floor(activeUser.xpPoints / 100) + 1} Citizen
                </span>

                <div style={{ margin: '20px 0 10px 0', textAlign: 'left' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'hsl(var(--text-secondary))', marginBottom: '6px' }}>
                    <span>XP progress to Level {Math.floor(activeUser.xpPoints / 100) + 2}</span>
                    <strong>{activeUser.xpPoints % 100} / 100 XP</strong>
                  </div>
                  {/* Progress bar container */}
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '99px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${activeUser.xpPoints % 100}%`,
                      height: '100%',
                      background: 'linear-gradient(95deg, hsl(var(--primary)), hsl(var(--cyan)))',
                      borderRadius: '99px',
                      transition: 'width 0.4s ease'
                    }}></div>
                  </div>
                </div>
              </div>

              {/* Statistics Grid */}
              <div className="glass-card" style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div style={{ textAlign: 'center', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                  <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '4px' }}>REPORTS MADE</span>
                  <strong style={{ fontSize: '1.5rem', color: 'white' }}>{activeUser.reportsCount}</strong>
                </div>
                <div style={{ textAlign: 'center', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                  <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '4px' }}>VERIFICATIONS</span>
                  <strong style={{ fontSize: '1.5rem', color: 'white' }}>{activeUser.verifiedCount}</strong>
                </div>
              </div>
            </div>

            {/* Right Column: Badges Grid & My Reports */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Badges container */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.15rem', color: 'white', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Award size={18} style={{ color: 'hsl(var(--primary))' }} />
                  Unlocked Badges & Rewards
                </h3>
                
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '16px'
                }}>
                  {db.badges.map(badge => {
                    const isUnlocked = activeUser.badgeIds.includes(badge.id);
                    return (
                      <div 
                        key={badge.id}
                        style={{
                          background: isUnlocked ? 'rgba(139, 92, 246, 0.05)' : 'rgba(255, 255, 255, 0.01)',
                          border: isUnlocked ? '1px solid rgba(139, 92, 246, 0.25)' : '1px solid rgba(255, 255, 255, 0.03)',
                          borderRadius: '12px',
                          padding: '14px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          opacity: isUnlocked ? 1 : 0.45,
                          transition: 'all 0.3s'
                        }}
                      >
                        <span style={{ fontSize: '2.25rem' }}>{badge.icon}</span>
                        <div>
                          <strong style={{ fontSize: '0.85rem', color: 'white', display: 'block' }}>{badge.name}</strong>
                          <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))', display: 'block', marginTop: '2px' }}>
                            {badge.description}
                          </span>
                          {isUnlocked ? (
                            <span style={{ fontSize: '0.65rem', color: 'hsl(var(--emerald))', fontWeight: 'bold', display: 'block', marginTop: '4px' }}>
                              UNLOCKED (+{badge.xpReward} XP)
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.65rem', color: 'hsl(var(--text-muted))', display: 'block', marginTop: '4px' }}>
                              Locked
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* My Reports */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.15rem', color: 'white', marginBottom: '16px' }}>My Submitted Civic Reports</h3>
                
                {db.issues.filter(i => i.reporterId === activeUser.id).length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <span style={{ color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '12px', fontSize: '0.9rem' }}>
                      You haven't submitted any civic reports yet.
                    </span>
                    <button onClick={() => setCurrentPage('report')} className="btn-primary" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
                      Create Your First Report
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {db.issues
                      .filter(i => i.reporterId === activeUser.id)
                      .map(issue => (
                        <div 
                          key={issue.id}
                          onClick={() => {
                            setSelectedIssueId(issue.id);
                            setCurrentPage('map');
                          }}
                          style={{
                            background: 'rgba(255, 255, 255, 0.02)',
                            border: '1px solid var(--border-light)',
                            borderRadius: '8px',
                            padding: '12px 16px',
                            cursor: 'pointer',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            transition: 'all 0.2s'
                          }}
                          className="my-report-row"
                        >
                          <div>
                            <div style={{ display: 'flex', gap: '6px', marginBottom: '4px' }}>
                              <span className={`badge badge-${issue.category}`}>{issue.category}</span>
                              <span className={`badge badge-${issue.status}`}>{issue.status}</span>
                            </div>
                            <strong style={{ fontSize: '0.9rem', color: 'white' }}>{issue.title}</strong>
                            <span style={{ display: 'block', fontSize: '0.75rem', color: 'hsl(var(--text-muted))', marginTop: '2px' }}>
                              {issue.addressText.slice(0, 70)}...
                            </span>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                            <div style={{ textAlign: 'right' }}>
                              <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))' }}>Upvotes</span>
                              <strong style={{ display: 'block', color: 'white', fontSize: '0.9rem' }}>{issue.upvoteCount}</strong>
                            </div>
                            <ChevronRight size={18} style={{ color: 'hsl(var(--text-muted))' }} />
                          </div>
                        </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

        {/* 5. AUTHORITY DASHBOARD */}
        {currentPage === 'authority' && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Header metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div className="glass-card" style={{ padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '4px' }}>
                  ASSIGNED TO ME
                </span>
                <strong style={{ fontSize: '1.75rem', color: 'white' }}>
                  {db.issues.filter(i => i.assignedTo === activeUser.id).length}
                </strong>
              </div>
              <div className="glass-card" style={{ padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '4px' }}>
                  UNRESOLVED CRITICALS
                </span>
                <strong style={{ fontSize: '1.75rem', color: 'hsl(var(--rose))' }}>
                  {db.issues.filter(i => i.severity === 'critical' && i.status !== 'resolved').length}
                </strong>
              </div>
              <div className="glass-card" style={{ padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '4px' }}>
                  COMMUNITY BACKED (&gt;=5 votes)
                </span>
                <strong style={{ fontSize: '1.75rem', color: 'hsl(var(--cyan))' }}>
                  {db.issues.filter(i => i.upvoteCount >= 5 && i.status !== 'resolved').length}
                </strong>
              </div>
              <div className="glass-card" style={{ padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', display: 'block', marginBottom: '4px' }}>
                  RESOLVED TO DATE
                </span>
                <strong style={{ fontSize: '1.75rem', color: 'hsl(var(--emerald))' }}>
                  {db.issues.filter(i => i.status === 'resolved').length}
                </strong>
              </div>
            </div>

            {/* Filter and Table Grid layout */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '20px' }}>
              
              {/* Left Column Table list of issues */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.15rem', color: 'white', marginBottom: '16px' }}>Municipal Service Complaints</h3>
                
                {/* Custom Filters for Table */}
                <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                  <input 
                    type="text" 
                    placeholder="Search by ID or title..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      flex: 1,
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-light)',
                      color: 'white',
                      borderRadius: '6px',
                      padding: '6px 12px',
                      fontSize: '0.85rem'
                    }}
                  />
                  <select 
                    value={filterSeverity} 
                    onChange={(e) => setFilterSeverity(e.target.value)}
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-light)',
                      color: 'white',
                      borderRadius: '6px',
                      padding: '6px',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="all">Severity</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                  <select 
                    value={filterStatus} 
                    onChange={(e) => setFilterStatus(e.target.value)}
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-light)',
                      color: 'white',
                      borderRadius: '6px',
                      padding: '6px',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="all">Status</option>
                    <option value="reported">Reported</option>
                    <option value="verified">Verified</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-light)', color: 'hsl(var(--text-muted))' }}>
                        <th style={{ padding: '10px 8px' }}>Complaint Title</th>
                        <th style={{ padding: '10px 8px' }}>Category</th>
                        <th style={{ padding: '10px 8px' }}>Severity</th>
                        <th style={{ padding: '10px 8px' }}>Upvotes</th>
                        <th style={{ padding: '10px 8px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredIssues.map(issue => (
                        <tr 
                          key={issue.id}
                          onClick={() => setSelectedIssueId(issue.id)}
                          style={{
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                            cursor: 'pointer',
                            background: selectedIssueId === issue.id ? 'rgba(139, 92, 246, 0.08)' : 'transparent'
                          }}
                        >
                          <td style={{ padding: '12px 8px', color: 'white', fontWeight: 'bold' }}>{issue.title}</td>
                          <td style={{ padding: '12px 8px' }}>
                            <span className={`badge badge-${issue.category}`}>{issue.category}</span>
                          </td>
                          <td style={{ padding: '12px 8px' }}>
                            <span className={`badge badge-${issue.severity}`}>{issue.severity}</span>
                          </td>
                          <td style={{ padding: '12px 8px', color: 'white' }}>{issue.upvoteCount}</td>
                          <td style={{ padding: '12px 8px' }}>
                            <span className={`badge badge-${issue.status}`}>{issue.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Right Column details action pane */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {selectedIssue ? (
                  <div className="glass-card" style={{ padding: '20px' }}>
                    <h3 style={{ fontSize: '1.1rem', color: 'white', marginBottom: '8px' }}>Update Complaint ID: #{selectedIssue.id.slice(4)}</h3>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', marginBottom: '16px' }}>
                      <div>
                        <span>Title:</span>
                        <strong style={{ display: 'block', color: 'white', marginTop: '2px' }}>{selectedIssue.title}</strong>
                      </div>
                      <div>
                        <span>Location:</span>
                        <strong style={{ display: 'block', color: 'white', marginTop: '2px' }}>{selectedIssue.addressText}</strong>
                      </div>
                      <div>
                        <span>Current Status:</span>
                        <strong style={{ display: 'block', color: '#f59e0b', marginTop: '2px' }}>{selectedIssue.status.toUpperCase()}</strong>
                      </div>
                    </div>

                    <img 
                      src={selectedIssue.mediaUrls[0]} 
                      alt="Review source"
                      style={{ width: '100%', height: '140px', objectFit: 'cover', borderRadius: '6px', marginBottom: '16px', border: '1px solid var(--border-light)' }}
                    />

                    {/* Quick status progression actions form */}
                    <form onSubmit={(e) => e.preventDefault()} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'white', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>
                          Add Work Log / Resolution Note:
                        </label>
                        <textarea 
                          placeholder="e.g. Dispatched the water division team to patch the joint."
                          value={resolutionNote}
                          onChange={(e) => setResolutionNote(e.target.value)}
                          rows="3"
                          style={{
                            width: '100%',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-light)',
                            color: 'white',
                            padding: '8px',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            resize: 'none'
                          }}
                        ></textarea>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {selectedIssue.status === 'reported' && (
                          <button 
                            type="button"
                            onClick={() => handleUpdateStatus(selectedIssue.id, 'verified')}
                            className="btn-primary"
                            style={{ background: 'linear-gradient(135deg, #06b6d4, #0891b2)', justifyContent: 'center' }}
                          >
                            Mark as Verified
                          </button>
                        )}
                        {(selectedIssue.status === 'reported' || selectedIssue.status === 'verified') && (
                          <button 
                            type="button"
                            onClick={() => handleUpdateStatus(selectedIssue.id, 'in_progress')}
                            className="btn-primary"
                            style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', justifyContent: 'center' }}
                          >
                            Dispatch & Set In Progress
                          </button>
                        )}
                        {selectedIssue.status === 'in_progress' && (
                          <button 
                            type="button"
                            onClick={() => handleUpdateStatus(selectedIssue.id, 'resolved')}
                            className="btn-primary"
                            style={{ background: 'linear-gradient(135deg, #10b981, #059669)', justifyContent: 'center' }}
                          >
                            Mark Resolved (+50 XP to Reporter)
                          </button>
                        )}
                        
                        {selectedIssue.status !== 'resolved' && (
                          <button 
                            type="button"
                            onClick={() => handleUpdateStatus(selectedIssue.id, 'rejected')}
                            className="btn-secondary"
                            style={{ justifyContent: 'center', borderColor: 'rgba(244,63,94,0.3)', color: 'hsl(var(--rose))' }}
                          >
                            Reject Report
                          </button>
                        )}
                      </div>
                    </form>
                  </div>
                ) : (
                  <div className="glass-card" style={{ padding: '40px', textTransform: 'center', color: 'hsl(var(--text-muted))', fontSize: '0.85rem' }}>
                    Select a row from the complaints table to edit status, assign technicians, or upload resolution logs.
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

        {/* 6. LEADERBOARD */}
        {currentPage === 'leaderboard' && (
          <div className="animate-fade-in" style={{ maxWidth: '800px', margin: '0 auto' }}>
            <div className="glass-card" style={{ padding: '30px' }}>
              <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                <h2 style={{ fontSize: '1.75rem', color: 'white', marginBottom: '6px' }}>Civic Leaderboard</h2>
                <span style={{ fontSize: '0.85rem', color: 'hsl(var(--text-muted))' }}>Recognizing citizens making the greatest impact on hyperlocal safety</span>
              </div>

              {/* Podium for top 3 */}
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'flex-end',
                gap: '20px',
                marginBottom: '40px',
                paddingBottom: '20px',
                borderBottom: '1px solid var(--border-light)'
              }}>
                {/* 2nd Place */}
                {db.users[1] && (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ position: 'relative' }}>
                      <img 
                        src={db.users[1].avatarUrl} 
                        alt="2nd place avatar" 
                        style={{ width: '60px', height: '60px', borderRadius: '50%', border: '2.5px solid #cbd5e1' }}
                      />
                      <span style={{
                        position: 'absolute', bottom: '-4px', right: '18px', background: '#cbd5e1', color: '#0b0f19',
                        borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '0.75rem', fontWeight: 'bold'
                      }}>2</span>
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'white', fontWeight: 'bold', marginTop: '8px' }}>
                      {db.users[1].fullName.split(' ')[0]}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{db.users[1].xpPoints} XP</span>
                    <div style={{ height: '50px', width: '80px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px 6px 0 0', marginTop: '10px' }}></div>
                  </div>
                )}

                {/* 1st Place */}
                {db.users[2] && (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ position: 'relative' }}>
                      <img 
                        src={db.users[2].avatarUrl} 
                        alt="1st place avatar" 
                        style={{
                          width: '80px',
                          height: '80px',
                          borderRadius: '50%',
                          border: '3px solid hsl(var(--primary))',
                          boxShadow: '0 0 20px var(--primary-glow)'
                        }}
                      />
                      <span style={{
                        position: 'absolute', bottom: '-4px', right: '28px', background: 'hsl(var(--primary))', color: 'white',
                        borderRadius: '50%', width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '0.85rem', fontWeight: 'bold'
                      }}>1</span>
                    </div>
                    <span style={{ fontSize: '0.95rem', color: 'white', fontWeight: 'bold', marginTop: '8px' }}>
                      {db.users[2].fullName.split(' ')[0]}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#a78bfa' }}>{db.users[2].xpPoints} XP</span>
                    <div style={{ height: '80px', width: '100px', background: 'rgba(139, 92, 246, 0.1)', border: '1px solid rgba(139, 92, 246, 0.2)', borderRadius: '8px 8px 0 0', marginTop: '10px' }}></div>
                  </div>
                )}

                {/* 3rd Place */}
                {db.users[0] && (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ position: 'relative' }}>
                      <img 
                        src={db.users[0].avatarUrl} 
                        alt="3rd place avatar" 
                        style={{ width: '55px', height: '55px', borderRadius: '50%', border: '2px solid #b45309' }}
                      />
                      <span style={{
                        position: 'absolute', bottom: '-4px', right: '16px', background: '#b45309', color: 'white',
                        borderRadius: '50%', width: '18px', height: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '0.7rem', fontWeight: 'bold'
                      }}>3</span>
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'white', fontWeight: 'bold', marginTop: '8px' }}>
                      {db.users[0].fullName.split(' ')[0]}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#b45309' }}>{db.users[0].xpPoints} XP</span>
                    <div style={{ height: '35px', width: '80px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px 6px 0 0', marginTop: '10px' }}></div>
                  </div>
                )}
              </div>

              {/* Complete table list */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {db.users
                  .filter(u => u.role !== 'admin' && u.role !== 'authority')
                  .sort((a, b) => b.xpPoints - a.xpPoints)
                  .map((user, idx) => (
                    <div 
                      key={user.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '12px 18px',
                        background: user.id === activeUser.id ? 'rgba(139,92,246,0.1)' : 'rgba(255,255,255,0.02)',
                        border: user.id === activeUser.id ? '1px solid rgba(139,92,246,0.3)' : '1px solid var(--border-light)',
                        borderRadius: '10px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ width: '24px', fontWeight: 'bold', color: 'hsl(var(--text-muted))', fontSize: '0.9rem' }}>
                          #{idx + 1}
                        </span>
                        <img src={user.avatarUrl} alt={user.fullName} style={{ width: '36px', height: '36px', borderRadius: '50%' }} />
                        <div>
                          <strong style={{ fontSize: '0.9rem', color: 'white' }}>{user.fullName}</strong>
                          <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-muted))', display: 'block' }}>
                            {user.reportsCount} Reports | {user.verifiedCount} Verifications
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: 'white' }}>{user.xpPoints} XP</span>
                          <span style={{ display: 'block', fontSize: '0.65rem', color: '#a78bfa' }}>
                            Lvl {Math.floor(user.xpPoints/100) + 1}
                          </span>
                        </div>
                      </div>
                    </div>
                ))}
              </div>

            </div>
          </div>
        )}

      </main>

      {/* Footer bar */}
      <footer style={{
        background: 'rgba(10, 14, 25, 0.9)',
        borderTop: '1px solid var(--border-light)',
        padding: '20px 24px',
        textAlign: 'center',
        marginTop: 'auto'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'hsl(var(--text-muted))' }}>
          <span>© 2026 Community Hero Inc. Built for Hyperlocal Civic Solutions.</span>
          <div style={{ display: 'flex', gap: '16px' }}>
            <span style={{ color: 'white', cursor: 'pointer' }} onClick={() => setCurrentPage('landing')}>Landing Page</span>
            <span>•</span>
            <span style={{ color: 'white', cursor: 'pointer' }} onClick={() => setCurrentPage('map')}>Map Directory</span>
          </div>
        </div>
      </footer>

      {/* Unlocked Toast Badge Display Notification */}
      {toastBadge && (
        <div className="badge-toast">
          <span style={{ fontSize: '2.5rem' }}>{toastBadge.icon}</span>
          <div>
            <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'hsl(var(--cyan))', letterSpacing: '0.05em', fontWeight: 'bold' }}>
              🌟 NEW BADGE UNLOCKED!
            </span>
            <h4 style={{ color: 'white', fontSize: '1rem', marginTop: '2px' }}>{toastBadge.name}</h4>
            <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem', marginTop: '2px' }}>
              Earned {toastBadge.xpReward} XP: {toastBadge.description}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
