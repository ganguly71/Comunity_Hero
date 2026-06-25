# 🇮🇳 Community Hero - Hyperlocal Civic Resolution Platform

**Community Hero** is a modern, high-aesthetic web application designed to empower citizens and digitize local civic grievance management. By bridging the gap between local residents and municipal administration, the platform allows communities to flag, track, and solve infrastructure issues transparently.

---

## 🚀 Key Architectural Pillars

### 1. Public-First Transparency Approach
* **Open Ledger**: All reported issues, locations, photos, progress timelines, and comments are fully public. Any visitor can browse the interactive map and review the state of local infrastructure.
* **Citizen Veto (Challenge System)**: When a District Manager marks an issue as `DONE`, citizens have a **90-day window** to challenge the claim if the work is incomplete or unsatisfactory, reopening the ticket.

### 2. Hierarchical Governance Structure
The application enforces strict role-based access control (RBAC) across four tiers:
* **🛡️ Global Admin**: Oversees the entire system. Can create/manage State Managers and review/delete the secure mail communication logs.
* **🏛️ State Manager**: Oversees all districts within their state. Inspects district-specific progress, views state-wide leaderboard performance, and manages District Managers.
* **🔧 District Manager**: Oversees local issues within their assigned district. Investigates reports, updates government statuses (`NOT VISITED`, `ONGOING`, `DONE`), and contacts citizen reporters securely.
* **👤 Citizen**: The boots on the ground. Reports local issues, comments on threads, upvotes/downvotes tickets to raise urgency, and manages their gamified reputation points.

### 3. Gamification of Civic Power
Citizens earn points and climb the community leaderboards by contributing to their neighborhood:
* **Sign Up Bonus**: `+50 Points`
* **Flagging a New Issue**: `+15 Points`
* **Upvoting/Downvoting**: `+5 Points`
* **Commenting on an Issue**: `+2 Points`
* **Successful Issue Resolution (Gov't DONE)**: `+50 Points` (to the reporter) and `+25 Points` (to the solver/verifier)

### 4. Interactive Satellite Map
* Powered by **Leaflet.js**, the satellite view displays real-time pins for all active civic grievances.
* Pins are dynamically color-coded by **Intensity** (Red: High, Yellow: Medium, Blue: Low) and **Status** (Open, Under Review, In Progress, Resolved).
* **GPS Boundaries**: Issue reporting is strictly verified to be within **10 km of the user's current GPS location** to prevent false or out-of-jurisdiction reports.

### 5. Secure Communications & Email Routing
* **Anonymous Connections**: District Managers can contact reporters directly via the portal. The manager *never* sees the citizen's personal email address. 
* **Secure Forwarding**: The email is dispatched from the system domain with the `Reply-To` header set to the manager's official address, allowing secure direct communication.
* **Mailing Integrations (Brevo SMTP)**:
  * **Onboarding Greeting**: Emailed to newly registered citizens.
  * **Report Receipts**: Instantly emailed to the reporter upon successfully filing a grievance.
  * **Status Notifications**: Dispatched to the citizen when a manager updates the issue state.
  * **Weekly digests**: Automatic cron checks flag stale issues (>7 days unresolved) or popular issues (>=10 votes) and email a digest report to the respective District Managers.

---

## 🛠️ Technology Stack

* **Backend Framework**: Python 3.11 / Flask, Flask-Login (Authentication & Session State)
* **ORM & Database**: SQLAlchemy / PostgreSQL (hosted via Supabase), SQLite for local development
* **Cloud Storage**: Supabase Bucket Storage (holds uploaded photos/videos of civic issues)
* **Artificial Intelligence**: **Google Gemini AI (gemini-1.5-flash)** (dynamically reads issue title + description and automatically categorizes it into Roads, Waste, Water, Streetlights, etc.)
* **Email Service**: **Brevo SMTP API**
* **Frontend Engine**: Vanilla HTML5, JavaScript (ES6+), CSS3
  * **Three.js**: Renders a waving, glowing Tiranga particle field background.
  * **Leaflet.js**: Handles vector mapping, custom marker rendering, and location tracking.

---

## 📂 Codebase Overview

* [app.py](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/app.py): Core Flask application containing all routes, AI categorization logic, and Brevo mailing functions.
* [models.py](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/models.py): Declarative database schemas (`User`, `Issue`, `Comment`, `Vote`, `UpdateLog`, `SentMail`).
* [static/js/particles.js](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/static/js/particles.js): Three.js particle wave physics and Ashok Chakra SVG path render coordinates.
* [templates/](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/templates/):
  * [base.html](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/templates/base.html): Navigation, branding, and layout wrapper.
  * [home.html](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/templates/home.html): Responsive landing page with platform highlights.
  * [index.html](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/templates/index.html): Live satellite map and reporting dashboard.
  * [dashboard.html](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/templates/dashboard.html): Custom user stats, profile updates, and admin communication logs.
  * [leaderboard.html](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/templates/leaderboard.html): Citizen and district ranking metrics.

---

## 💻 Local Setup & Installation

1. **Clone and Navigate**:
   ```bash
   git clone <repository-url>
   cd Vibe2Ship
   ```

2. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///community_hero.db
   GEMINI_API_KEY=your_gemini_api_key
   BREVO_API_KEY=your_brevo_api_key
   BREVO_SENDER_EMAIL=notifications@yourdomain.com
   BREVO_SENDER_NAME="Community Hero"
   ```

3. **Initialize the Database**:
   Run the CLI seeder command to automatically initialize tables and seed **10 mock citizens, 20 detailed issues, votes, comments, and logs**:
   ```bash
   flask init-db
   ```

4. **Launch Server**:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:5000` in your web browser.

---

## 👤 Mock Credentials for Demo

Access different tier roles with these seeded accounts:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Global Admin** | `admin` | `password123` |
| **State Manager (Karnataka)** | `state_mgr_karnataka` | `password123` |
| **District Manager (Bangalore)** | `dist_mgr_blr` | `password123` |
| **Citizen (Alex)** | `citizen_alex` | `password123` |
| **Citizen (Priya - High Points)** | `citizen_priya` | `password123` |

---

## ☁️ Deployment

### 🐳 Google Cloud Run Deployment
Deploy containerized directly using the provided [Dockerfile](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/Dockerfile) and [deploy.bat](file:///c:/Users/adity/OneDrive/ドキュメント/Vibe2Ship/deploy.bat) script:
```powershell
gcloud run deploy community-hero --source . --platform managed --region us-central1 --allow-unauthenticated --set-env-vars "DATABASE_URL=...,GEMINI_API_KEY=...,SECRET_KEY=...,BREVO_API_KEY=..."
```
