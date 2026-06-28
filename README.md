<p align="center">
  <img src="https://i.ibb.co/MDFM8W7B/logo.png" alt="Community Hero Logo" width="520px">
</p>

# 🇮🇳 Community Hero - Hyperlocal Civic Resolution Platform


**Community Hero** is a modern, high-aesthetic web application designed to empower citizens and digitize local civic grievance management. By bridging the gap between local residents and municipal administration, the platform allows communities to flag, track, and solve infrastructure issues transparently.

---

## ☁️ Live Deployments

The platform is deployed and fully active on:
* **GCP Cloud Run**: [https://community-hero-737666763746.us-central1.run.app](https://community-hero-737666763746.us-central1.run.app)
* **Render**: [https://comunity-hero.onrender.com](https://comunity-hero.onrender.com)

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

### 3. Interactive Satellite Map
* Powered by **Leaflet.js**, the satellite view displays real-time pins for all active civic grievances.
* Pins are dynamically color-coded by **Intensity** (Red: High, Yellow: Medium, Blue: Low) and **Status** (Open, Under Review, In Progress, Resolved).
* **GPS Boundaries**: Issue reporting is strictly verified to be within **10 km of the user's current GPS location** (received live via geolocation) to prevent false or out-of-jurisdiction reports.
* **Locate Issue by ID**: Locate any active or resolved issue using its numeric ID. For Admins and State Managers, searching for an issue outside the currently inspected district will trigger a prompt to switch inspection scopes, automatically reloading the session under the target district and auto-selecting the issue.

### 4. Secure Anonymous Connections & Email Routing
* **Anonymous Connections**: District Managers can contact reporters directly via the portal. The manager *never* sees the citizen's personal email address, protecting citizen privacy.
* **Secure Forwarding**: The email is dispatched from the system domain with the `Reply-To` header set to the manager's official address, allowing secure direct communication.
* **Mailing Integrations (Brevo SMTP)**:
  * **Onboarding Greeting**: Emailed to newly registered citizens.
  * **Report Receipts**: Instantly emailed to the reporter upon successfully filing a grievance.
  * **Status Notifications**: Dispatched to the citizen when a manager updates the issue state.
  * **Weekly digests**: Automatic cron checks flag stale issues (>7 days unresolved) or popular issues (>=10 votes) and email a digest report to the respective District Managers.
  * **Unmanaged Grievance Alerts**: Sends a real-time list of all active unmanaged issues in a state to the respective State Manager when a new managerless issue is reported. If the state has no manager, the alert automatically escalates to all Global Admins. Once a manager is assigned, their issues are dynamically excluded from subsequent digests.

---

## 🏆 Gamification & Points Rules

To incentivize active civic contribution, the platform incorporates a points-based reputation hierarchy:

### Points Rules Table
| Activity | Points Awarded | Target |
| :--- | :--- | :--- |
| **Account Creation** | `+50 Points` | New Citizen |
| **Flagging a New Issue** | `+15 Points` | Reporter |
| **Upvoting/Downvoting** | `+5 Points` | Citizen Reporter |
| **Commenting on an Issue** | `+2 Points` | Contributing User |
| **Issue Resolved (Gov't Status DONE)** | `+50 Points` | Original Reporter |
| **Resolving/Verifying Issue** | `+25 Points` | District Manager / Resolver |

### Leaderboard Tiers
1. **Citizen Rankings**: Ranks active citizens globally based on accumulated contribution points, highlighting the community's top contributors.
2. **Inter-District Performance**: Ranks districts within a state based on their percentage of resolved issues (`govt_status = DONE`).
3. **Inter-State Standings**: Compare state-wide resolution statistics, creating healthy competition between local municipal bodies.

---

## 💬 Citizen Collaboration (Voting & Comments)

* **Area-Locked Comments**: Citizens can participate in comment threads and debate local issues only within their registered state and district, preventing spam from external regions.
* **Dynamic Voting System**: Upvotes and downvotes bubble high-priority issues to the top. Issues accumulating 10 or more net votes are flagged in the system and automatically emailed to the respective District Manager in the weekly priority digest.

---

## 📊 Advanced Data Analytics

The **Impact Stats** panel provides real-time data transparency:
* **Resolution Rate**: Computes the percentage of resolved issues (`Resolved` / `Total Issues`) for any selected state or district.
* **Category Distribution**: Renders comparative metrics showing the volume of issues across different sectors (Roads, Water, Waste, Streetlights, etc.).
* **Intensity Ratios**: Visualizes the proportion of High, Medium, and Low intensity hazards.
* **Community Engagement Indexes**: Tracks metrics such as the average comments and votes per issue to measure community involvement.

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


## 👤 Mock Credentials for Demo

Access different tier roles with these seeded accounts (password for all seeded accounts is `Password123`):

### 🛡️ Admin & State Managers
| Role | Area | Username | Email |
| :--- | :--- | :--- | :--- |
| **Global Admin** | *Global* | `admin` | `admin@communityhero.gov` |
| **State Manager** | Karnataka | `state_mgr_karnataka` | `karnataka@communityhero.gov` |
| **State Manager** | Maharashtra | `state_mgr_maharashtra` | `maharashtra@communityhero.gov` |
| **State Manager** | Delhi | `state_mgr_delhi` | `delhi@communityhero.gov` |

### 🏛️ District Managers
| Role | State | District | Username | Email |
| :--- | :--- | :--- | :--- | :--- |
| **District Manager** | Karnataka | Bangalore Urban | `dist_mgr_blr` | `bangalore@communityhero.gov` |
| **District Manager** | Maharashtra | Pune | `dist_mgr_pune` | `pune@communityhero.gov` |
| **District Manager** | Delhi | New Delhi | `dist_mgr_ndls` | `newdelhi@communityhero.gov` |

### 👤 Seeded Citizens
| Username | State | District | Email | Points |
| :--- | :--- | :--- | :--- | :--- |
| `citizen_alex` | Karnataka | Bangalore Urban | `alex@example.com` | `120` |
| `jane_doe` | Karnataka | Bangalore Urban | `jane@example.com` | `85` |
| `citizen_priya` | Karnataka | Bangalore Urban | `priya@example.com` | `240` |
| `citizen_sunita` | Karnataka | Bangalore Urban | `sunita@example.com` | `150` |
| `citizen_pune` | Maharashtra | Pune | `pune_citizen@example.com` | `50` |
| `citizen_rahul` | Maharashtra | Pune | `rahul@example.com` | `180` |
| `citizen_vivek` | Maharashtra | Pune | `vivek@example.com` | `310` |
| `citizen_delhi` | Delhi | New Delhi | `delhi_citizen@example.com` | `60` |
| `citizen_amit` | Delhi | New Delhi | `amit@example.com` | `95` |
| `citizen_ananya` | Delhi | New Delhi | `ananya@example.com` | `40` |