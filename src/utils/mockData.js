// Mock Database and Helper Functions for Local Storage Persistence

export const INITIAL_WARDS = [
  { id: "w1", name: "Indiranagar", city: "Bengaluru", boundary_geojson: null },
  { id: "w2", name: "Koramangala", city: "Bengaluru", boundary_geojson: null },
  { id: "w3", name: "HSR Layout", city: "Bengaluru", boundary_geojson: null },
  { id: "w4", name: "Whitefield", city: "Bengaluru", boundary_geojson: null }
];

export const INITIAL_BADGES = [
  { id: "b1", name: "First Reporter", icon: "🏅", description: "Submit your first report", xpReward: 50, conditionType: "reports_count", conditionValue: 1 },
  { id: "b2", name: "Neighborhood Watch", icon: "👁️", description: "Verify 5 issues reported by others", xpReward: 100, conditionType: "verified_count", conditionValue: 5 },
  { id: "b3", name: "Problem Solver", icon: "🛠️", description: "Have 3 of your reported issues successfully resolved", xpReward: 150, conditionType: "resolved_count", conditionValue: 3 },
  { id: "b4", name: "Ward Champion", icon: "👑", description: "Submit 10 reports in a single month", xpReward: 200, conditionType: "reports_count", conditionValue: 10 }
];

export const INITIAL_USERS = [
  {
    id: "u1",
    email: "aditya@communityhero.in",
    fullName: "Aditya Kumar",
    phone: "+91 98765 43210",
    avatarUrl: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&h=150",
    role: "citizen",
    wardId: "w1",
    xpPoints: 120,
    badgeIds: ["b1"],
    reportsCount: 3,
    verifiedCount: 4,
    createdAt: "2026-05-10T10:00:00Z"
  },
  {
    id: "u2",
    email: "priya@communityhero.in",
    fullName: "Priya Sharma",
    phone: "+91 98123 45678",
    avatarUrl: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&h=150",
    role: "citizen",
    wardId: "w2",
    xpPoints: 240,
    badgeIds: ["b1", "b2"],
    reportsCount: 8,
    verifiedCount: 12,
    createdAt: "2026-04-15T09:30:00Z"
  },
  {
    id: "u3",
    email: "rohan.mod@communityhero.in",
    fullName: "Rohan Sen",
    phone: "+91 99000 88888",
    avatarUrl: "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=150&h=150",
    role: "moderator",
    wardId: "w3",
    xpPoints: 350,
    badgeIds: ["b1", "b2", "b3"],
    reportsCount: 12,
    verifiedCount: 45,
    createdAt: "2026-01-20T14:00:00Z"
  },
  {
    id: "u4",
    email: "officer.ramesh@bbmp.gov.in",
    fullName: "Officer Ramesh Gowda",
    phone: "+91 98888 77777",
    avatarUrl: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&h=150",
    role: "authority",
    wardId: "w1",
    xpPoints: 0,
    badgeIds: [],
    reportsCount: 0,
    verifiedCount: 0,
    createdAt: "2025-11-01T08:00:00Z"
  },
  {
    id: "u5",
    email: "admin@communityhero.in",
    fullName: "Super Admin",
    phone: "+91 90000 00000",
    avatarUrl: "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=150&h=150",
    role: "admin",
    wardId: "w3",
    xpPoints: 10,
    badgeIds: [],
    reportsCount: 0,
    verifiedCount: 0,
    createdAt: "2025-10-01T08:00:00Z"
  }
];

export const INITIAL_ISSUES = [
  {
    id: "iss1",
    title: "Deep Pothole on Indiranagar 100ft Road",
    description: "Huge pothole right in the middle of the road near the corner turn. Causes vehicles to swerve dangerously, especially two-wheelers at night. Needs immediate asphalt filling.",
    category: "pothole",
    severity: "critical",
    status: "verified",
    mediaUrls: ["https://images.unsplash.com/photo-1515162305285-0293e4767cc2?auto=format&fit=crop&w=800&q=80"],
    latitude: 12.9784,
    longitude: 77.6408,
    addressText: "Indiranagar 100 Feet Rd, Hal 2nd Stage, Indiranagar, Bengaluru, Karnataka 560038",
    wardId: "w1",
    reporterId: "u2",
    assignedTo: null,
    aiCategory: "pothole",
    aiConfidence: 0.96,
    upvoteCount: 15,
    isDuplicate: false,
    duplicateOf: null,
    createdAt: "2026-06-22T08:30:00Z",
    updatedAt: "2026-06-22T10:15:00Z",
    resolvedAt: null
  },
  {
    id: "iss2",
    title: "Broken Streetlight Near Metro Station",
    description: "The streetlight has been flicking for a week and has now completely died. The alley is pitch dark and unsafe for commuters walking home late.",
    category: "streetlight",
    severity: "high",
    status: "in_progress",
    mediaUrls: ["https://images.unsplash.com/photo-1509024644558-2f56ce76c490?auto=format&fit=crop&w=800&q=80"],
    latitude: 12.9722,
    longitude: 77.6320,
    addressText: "Chinmaya Mission Hospital Rd, Indiranagar, Bengaluru, Karnataka 560038",
    wardId: "w1",
    reporterId: "u1",
    assignedTo: "u4",
    aiCategory: "streetlight",
    aiConfidence: 0.98,
    upvoteCount: 7,
    isDuplicate: false,
    duplicateOf: null,
    createdAt: "2026-06-20T21:00:00Z",
    updatedAt: "2026-06-23T11:00:00Z",
    resolvedAt: null
  },
  {
    id: "iss3",
    title: "Major Water Pipe Leakage",
    description: "Clean water has been gushing out of a cracked pipe under the pavement. Massive wastage of water. It has formed a mini-pond.",
    category: "water_leak",
    severity: "medium",
    status: "resolved",
    mediaUrls: ["https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=800&q=80"],
    latitude: 12.9352,
    longitude: 77.6245,
    addressText: "80 Feet Rd, 4th Block, Koramangala, Bengaluru, Karnataka 560034",
    wardId: "w2",
    reporterId: "u2",
    assignedTo: "u4",
    aiCategory: "water_leak",
    aiConfidence: 0.94,
    upvoteCount: 22,
    isDuplicate: false,
    duplicateOf: null,
    createdAt: "2026-06-18T07:15:00Z",
    updatedAt: "2026-06-21T17:30:00Z",
    resolvedAt: "2026-06-21T17:30:00Z"
  },
  {
    id: "iss4",
    title: "Illegal Garbage Dumping on Sidewalk",
    description: "Tons of plastic waste and organic garbage dumped on the corner of the layout park. It is starting to smell awful and attracting stray dogs.",
    category: "waste",
    severity: "critical",
    status: "reported",
    mediaUrls: ["https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80"],
    latitude: 12.9116,
    longitude: 77.6388,
    addressText: "24th Main Rd, Sector 2, HSR Layout, Bengaluru, Karnataka 560102",
    wardId: "w3",
    reporterId: "u1",
    assignedTo: null,
    aiCategory: "waste",
    aiConfidence: 0.99,
    upvoteCount: 4,
    isDuplicate: false,
    duplicateOf: null,
    createdAt: "2026-06-24T09:00:00Z",
    updatedAt: "2026-06-24T09:00:00Z",
    resolvedAt: null
  },
  {
    id: "iss5",
    title: "Cracked Road and Caved-in Edge",
    description: "The side of the asphalt has eroded and caved in. Heavy vehicles parking on the shoulder could trigger a slide or roll over.",
    category: "road_damage",
    severity: "high",
    status: "reported",
    mediaUrls: ["https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80"],
    latitude: 12.9698,
    longitude: 77.7500,
    addressText: "ITPL Main Rd, Pattandur Agrahara, Whitefield, Bengaluru, Karnataka 560066",
    wardId: "w4",
    reporterId: "u2",
    assignedTo: null,
    aiCategory: "road_damage",
    aiConfidence: 0.89,
    upvoteCount: 8,
    isDuplicate: false,
    duplicateOf: null,
    createdAt: "2026-06-23T15:45:00Z",
    updatedAt: "2026-06-23T15:45:00Z",
    resolvedAt: null
  }
];

export const INITIAL_VERIFICATIONS = [
  { id: "v1", issueId: "iss1", userId: "u1", type: "upvote", createdAt: "2026-06-22T09:00:00Z" },
  { id: "v2", issueId: "iss1", userId: "u3", type: "seen", createdAt: "2026-06-22T09:30:00Z" },
  { id: "v3", issueId: "iss2", userId: "u2", type: "upvote", createdAt: "2026-06-21T08:00:00Z" },
  { id: "v4", issueId: "iss3", userId: "u1", type: "upvote", createdAt: "2026-06-18T10:00:00Z" },
  { id: "v5", issueId: "iss3", userId: "u3", type: "upvote", createdAt: "2026-06-18T12:00:00Z" }
];

export const INITIAL_COMMENTS = [
  { id: "c1", issueId: "iss1", userId: "u1", content: "I almost fell here on my scooter yesterday. Extremely dangerous, glad it was reported!", isAuthority: false, createdAt: "2026-06-22T09:05:00Z" },
  { id: "c2", issueId: "iss1", userId: "u3", content: "Verified this in person today. The depth is around 8 inches.", isAuthority: false, createdAt: "2026-06-22T09:32:00Z" },
  { id: "c3", issueId: "iss2", userId: "u4", content: "Assigned to the local electrical ward team. We are procuring a replacement bulb.", isAuthority: true, createdAt: "2026-06-23T11:00:00Z" },
  { id: "c4", issueId: "iss3", userId: "u4", content: "Water board team has successfully welded the pipe joint. The supply leak is stopped.", isAuthority: true, createdAt: "2026-06-21T17:30:00Z" }
];

export const INITIAL_STATUS_HISTORY = [
  { id: "sh1", issueId: "iss1", changedBy: "u2", oldStatus: null, newStatus: "reported", note: "Initial submission", createdAt: "2026-06-22T08:30:00Z" },
  { id: "sh2", issueId: "iss1", changedBy: "u3", oldStatus: "reported", newStatus: "verified", note: "Verified depth and safety threat", createdAt: "2026-06-22T10:15:00Z" },
  { id: "sh3", issueId: "iss2", changedBy: "u1", oldStatus: null, newStatus: "reported", note: "Initial submission", createdAt: "2026-06-20T21:00:00Z" },
  { id: "sh4", issueId: "iss2", changedBy: "u4", oldStatus: "reported", newStatus: "in_progress", note: "Assigned to electric maintenance team", createdAt: "2026-06-23T11:00:00Z" },
  { id: "sh5", issueId: "iss3", changedBy: "u2", oldStatus: null, newStatus: "reported", note: "Initial submission", createdAt: "2026-06-18T07:15:00Z" },
  { id: "sh6", issueId: "iss3", changedBy: "u4", oldStatus: "reported", newStatus: "in_progress", note: "Technicians dispatched", createdAt: "2026-06-19T09:00:00Z" },
  { id: "sh7", issueId: "iss3", changedBy: "u4", oldStatus: "in_progress", newStatus: "resolved", note: "Leak plugged, pavement restored.", createdAt: "2026-06-21T17:30:00Z" }
];

// Helper to initialize and retrieve from LocalStorage
const getStorageItem = (key, defaultValue) => {
  const item = localStorage.getItem(key);
  if (!item) {
    localStorage.setItem(key, JSON.stringify(defaultValue));
    return defaultValue;
  }
  return JSON.parse(item);
};

export const getDB = () => {
  return {
    users: getStorageItem("ch_users", INITIAL_USERS),
    issues: getStorageItem("ch_issues", INITIAL_ISSUES),
    verifications: getStorageItem("ch_verifications", INITIAL_VERIFICATIONS),
    comments: getStorageItem("ch_comments", INITIAL_COMMENTS),
    statusHistory: getStorageItem("ch_status_history", INITIAL_STATUS_HISTORY),
    wards: getStorageItem("ch_wards", INITIAL_WARDS),
    badges: getStorageItem("ch_badges", INITIAL_BADGES)
  };
};

export const saveDB = (db) => {
  localStorage.setItem("ch_users", JSON.stringify(db.users));
  localStorage.setItem("ch_issues", JSON.stringify(db.issues));
  localStorage.setItem("ch_verifications", JSON.stringify(db.verifications));
  localStorage.setItem("ch_comments", JSON.stringify(db.comments));
  localStorage.setItem("ch_status_history", JSON.stringify(db.statusHistory));
  localStorage.setItem("ch_wards", JSON.stringify(db.wards));
  localStorage.setItem("ch_badges", JSON.stringify(db.badges));
};

// Gamification rewards calculator
export const awardXP = (userId, actionType, db) => {
  const xpValues = {
    submit_report: 10,
    report_verified: 20,
    report_resolved: 50,
    verify_report: 5,
    comment: 2,
    first_report_day_bonus: 5
  };

  const xpGain = xpValues[actionType] || 0;
  if (xpGain === 0) return db;

  const updatedUsers = db.users.map(u => {
    if (u.id === userId) {
      const newXP = u.xpPoints + xpGain;
      // Recalculate stats based on operations
      let reportsCount = u.reportsCount;
      let verifiedCount = u.verifiedCount;
      
      if (actionType === "submit_report") {
        reportsCount += 1;
      }
      if (actionType === "verify_report") {
        verifiedCount += 1;
      }

      // Check badges conditions
      const earnedBadges = [...u.badgeIds];
      db.badges.forEach(badge => {
        if (!earnedBadges.includes(badge.id)) {
          if (badge.conditionType === "reports_count" && reportsCount >= badge.conditionValue) {
            earnedBadges.push(badge.id);
          } else if (badge.conditionType === "verified_count" && verifiedCount >= badge.conditionValue) {
            earnedBadges.push(badge.id);
          }
        }
      });

      return {
        ...u,
        xpPoints: newXP,
        reportsCount,
        verifiedCount,
        badgeIds: earnedBadges
      };
    }
    return u;
  });

  return { ...db, users: updatedUsers };
};

// Calculate priority score based on severity, upvotes, and days open
export const calculatePriorityScore = (issue) => {
  const severityWeights = {
    low: 1,
    medium: 2,
    high: 3,
    critical: 5
  };
  
  const createdDate = new Date(issue.createdAt);
  const diffTime = Math.abs(new Date() - createdDate);
  const daysOpen = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  const weight = severityWeights[issue.category] || severityWeights[issue.severity] || 1;
  const score = (weight * 3) + (issue.upvoteCount * 0.5) + (daysOpen * 0.2);
  return parseFloat(score.toFixed(1));
};

// Simulated AI Image Analysis Call
export const simulateAIAnalysis = (imageUrl, descriptionText) => {
  const text = (descriptionText || "").toLowerCase();
  
  // Categorize based on keywords in description
  let category = "other";
  let suggestedTitle = "Community Issue";
  let tags = ["Community"];
  let severity = "medium";
  let confidence = 0.85;

  if (text.includes("pot") || text.includes("cracked road") || text.includes("road") || text.includes("hole")) {
    category = "pothole";
    suggestedTitle = "Damaged Road Pothole";
    tags = ["RoadSafety", "Infrastructure", "Pothole"];
    severity = text.includes("deep") || text.includes("huge") ? "critical" : "high";
    confidence = 0.94;
  } else if (text.includes("water") || text.includes("leak") || text.includes("pipe") || text.includes("drain")) {
    category = "water_leak";
    suggestedTitle = "Water supply leakage";
    tags = ["WaterConservation", "UtilityLeak", "WaterBoard"];
    severity = text.includes("gushing") || text.includes("flood") ? "high" : "medium";
    confidence = 0.92;
  } else if (text.includes("light") || text.includes("bulb") || text.includes("dark") || text.includes("lamp")) {
    category = "streetlight";
    suggestedTitle = "Faulty Streetlight";
    tags = ["Streetlighting", "SafetyAtNight", "PowerGrid"];
    severity = text.includes("metro") || text.includes("dangerous") ? "high" : "medium";
    confidence = 0.96;
  } else if (text.includes("garbage") || text.includes("waste") || text.includes("dump") || text.includes("trash") || text.includes("plastic")) {
    category = "waste";
    suggestedTitle = "Accumulated Waste Dump";
    tags = ["WasteManagement", "Sanitation", "Hygiene"];
    severity = text.includes("stink") || text.includes("rats") ? "critical" : "high";
    confidence = 0.97;
  } else if (text.includes("road") || text.includes("cave") || text.includes("crack") || text.includes("shoulder")) {
    category = "road_damage";
    suggestedTitle = "Eroded Road Shoulder";
    tags = ["RoadDamage", "TrafficHazard", "Transit"];
    severity = "high";
    confidence = 0.88;
  }

  // Fallbacks if no keywords matched
  if (category === "other") {
    if (imageUrl) {
      // simulate classification from image
      category = "pothole";
      suggestedTitle = "Road Pothole Identified";
      tags = ["RoadSafety", "Pothole"];
      severity = "high";
      confidence = 0.91;
    } else {
      category = "other";
      suggestedTitle = descriptionText ? descriptionText.slice(0, 30) + "..." : "Civic Complaint";
      tags = ["GeneralIssue"];
      severity = "medium";
      confidence = 0.75;
    }
  }

  return {
    category,
    severity,
    tags,
    suggestedTitle,
    confidence
  };
};

// Check for duplicates within 150m (approx 0.00135 degrees latitude/longitude difference)
export const checkDuplicate = (lat, lng, category, issues) => {
  const RADIUS_DEG = 0.00135; // ~150 meters
  return issues.find(issue => {
    if (issue.category !== category) return false;
    if (issue.status === "resolved" || issue.status === "rejected") return false;
    
    const latDiff = Math.abs(issue.latitude - lat);
    const lngDiff = Math.abs(issue.longitude - lng);
    
    return latDiff <= RADIUS_DEG && lngDiff <= RADIUS_DEG;
  });
};
