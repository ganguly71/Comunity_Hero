# Community Hero - Hyperlocal Problem Solver 🦸‍♂️

Community Hero is a gamified hyperlocal problem-solving platform where citizens report local civic issues (potholes, broken lights, leakages, garbage), an on-device AI categorizes and tags them, neighbors verify reports to raise their priority, and municipal authorities receive a dedicated dashboard to assign, track, and resolve complaints.

This implementation features a high-fidelity interactive map and custom dashboard flows for different roles to simulate civic management.

---

## 🚀 Key Features

1. **Interactive Leaflet Map**:
   - Shows reported issues as pins color-coded by severity (Low, Medium, High, Critical) or resolution status.
   - Interactive popups with detail drawer expanders.
   
2. **On-Device AI Categorization (Gemini Simulation)**:
   - Analyzes report descriptions and photo data to auto-categorize (Potholes, Water leaks, Waste, Streetlights), tags topics, suggest titles, and score severity.
   
3. **Duplicate Detection Alert**:
   - Compares coordinate proximity and category of new submissions within 150 meters to active reports and warns citizens before submission, encouraging collaboration.

4. **Status Timeline & Comment Threads**:
   - Public logs detailing status changes from `Reported` ➔ `Verified` ➔ `In Progress` ➔ `Resolved`.
   - Thread discussion with styling highlighting official replies from municipal authority users.

5. **Gamification Layer**:
   - XP system awarding points for civic action (reporting, upvoting/verifying, commenting).
   - Unlocking badges: *First Reporter*, *Neighborhood Watch*, *Problem Solver*, *Ward Champion* with canvas confetti celebrations!
   
6. **Municipal Authority Dashboard**:
   - Complaint management panel to filter, search, read citizen comments, dispatch maintenance, log updates, and officially mark issues resolved.

7. **Judge Simulator Console**:
   - Dropdown bar at the top of the interface allowing instant switching between citizens, moderators, and officials to demo all flows.

---

## 🛠️ Tech Stack

- **Frontend Core**: React 18 & Vite (fast, zero-config hot reload)
- **Styling**: Modern CSS3 (Glassmorphism, dark slates, neon accents, keyframe animations, custom scrollbars)
- **Map rendering**: Leaflet.js (`react-leaflet`)
- **Icons**: Lucide React
- **Celebration Effects**: Canvas Confetti

---

## 📦 Directory Structure

```
Vibe2Ship/
├── index.html            # Imports Google Fonts and Leaflet styles
├── package.json          # Node dependencies and build scripts
├── vite.config.js        # Vite build tool config
├── README.md             # Documentation
└── src/
    ├── main.jsx          # Script entrypoint
    ├── App.jsx           # Master layout, navigation switcher, forms, maps, panels
    ├── index.css         # Styling system (dark slates, neon cyan/violet accents)
    └── utils/
        └── mockData.js   # LocalStorage database, seed data, AI scans, and XP logic
```

---

## 💻 Quick Start

To run the application locally:

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Launch development server**:
   ```bash
   npm run dev
   ```

3. **Open in browser**:
   Navigate to `http://localhost:3000` (or the port specified in terminal).

---

## 🔬 Simulation Walkthrough Guide

To evaluate the core features as a judge:

1. **Report a New Pothole**:
   - Click **Report Issue** in navigation.
   - Click **Acquire Current GPS Location** to simulate coordinates or click the map widget to drop a custom pin.
   - Select the **Pothole** preset photo.
   - Click **Trigger AI Auto-Fill Scan**. The AI will scan the text, fill in the category (Pothole), severity (High), generate tags, and construct a suggested title.
   - Click **Confirm & Submit Report**. Watch the canvas confetti celebration as your citizen account gains +10 XP!

2. **Upvote and Verify**:
   - You will be redirected to the interactive map. Click on the new marker pin or click another pin (e.g., Indiranagar pothole).
   - Expand details, read the comment threads, and click **I see this too**. Your account will instantly gain +5 XP.

3. **Log in as Authority**:
   - Go to the **Judge Simulator Console** at the very top of the screen.
   - Select **Officer Ramesh Gowda (AUTHORITY)** from the list.
   - Click **Gov Dashboard** in navigation. You will see a detailed table filterable by status/ward.
   - Select the reported pothole. Add a resolution note (e.g., *"Pothole repaired using asphalt mix"*), then click **Dispatch & Set In Progress**, followed by **Mark Resolved**.
   - Note the status changes dynamically, and the reporter is awarded +50 XP.

4. **Verify Gamification**:
   - Switch back to **Priya Sharma (CITIZEN)** or **Aditya Kumar (CITIZEN)**.
   - Click **My Profile** to view level upgrades, XP progress bars, and unlocked badges.
   - Click **Leaderboard** to review global citizen rankings based on active civic engagement.
