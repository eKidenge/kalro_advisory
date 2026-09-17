# KALRO Advisory — Climate-Resilient Agriculture Advisory System

A physics-informed AI advisory platform for Kenyan farmers, built on Django 6.
Turns climate data into farm-level decisions that are **accurate**, **explainable**,
and **physically consistent** — powered by a Physics-Informed Neural Network (PINN).

---

## Overview

KALRO (Kenya Agricultural and Livestock Research Organization) has developed over
50 climate-smart innovations and holds one of the largest fertilizer-trial databases
in Africa. Yet returns on research investment remain below 1% because farmers don't
have direct, trustworthy access to the resulting recommendations.

**KALRO Advisory** closes that gap with a PINN engine that:

- Embeds physical laws (water balance, nutrient cycling, energy conservation)
  directly into the model loss function
- Provides full explainability — every advisory exposes the factors that drove it
- Works in data-sparse regions by leaning on physics where data is thin
- Delivers via SMS (iShamba) and Selector Platform, so no smartphone is required
- Integrates with KALRO's existing systems: KAOP, AgData Hub, Selector, iShamba
## 1. OVERVIEW DIAGRAM
```mermaid
flowchart TD
    START([User Visits KALRO Advisory]) --> LAND[Public Landing Page]
    LAND --> STATS[Live Stats from DB]
    LAND --> CHOICE{Has Account?}

    CHOICE -- No --> REG[Registration]
    CHOICE -- Yes --> LOGIN[Login with OTP]

    REG --> VERIFY[OTP Verification]
    VERIFY --> LOGIN
    LOGIN --> AUDIT[Login Audit Log]
    AUDIT --> ROLE{Role?}

    ROLE -- Farmer --> FARMER[Farmer Dashboard]
    ROLE -- Extension Officer --> EXT[Extension Officer Dashboard]
    ROLE -- Researcher --> RES[Researcher Dashboard]
    ROLE -- KALRO Admin --> ADMIN[Admin Control Center]

    FARMER --> ADVISORY[Receive Advisories]
    EXT --> ADVISORY
    RES --> TRIALS[Trials & Analytics]
    ADMIN --> CONTROL[Full CRUD All Modules]

    ADVISORY --> SMS[SMS via iShamba]
    ADVISORY --> SELECTOR[Selector Platform]

    CONTROL --> MODULES[(All Modules)]
    TRIALS --> PINN[PINN Engine]
    PINN --> ADVISORY

    classDef entry fill:#4A90E2,stroke:#1F3A5F,color:#fff
    classDef auth fill:#7ED321,stroke:#3B6B00,color:#fff
    classDef role fill:#9013FE,stroke:#4A0A85,color:#fff
    classDef engine fill:#D0021B,stroke:#6B000D,color:#fff
    classDef delivery fill:#F5A623,stroke:#8B5A00,color:#fff
    class START,LAND,STATS,CHOICE entry
    class REG,LOGIN,VERIFY,AUDIT auth
    class FARMER,EXT,RES,ADMIN,ROLE,CONTROL,TRIALS role
    class PINN,ADVISORY,MODULES engine
    class SMS,SELECTOR delivery
```
## 2. Registration, OTP & Login Flow
```mermaid
flowchart TD
    A([Start]) --> B{Has Account?}

    B -- No --> C[Registration Form]
    C --> D[Name, Phone, Email, Role]
    D --> E{Valid Input?}
    E -- No --> F[Show Errors] --> C
    E -- Yes --> G[Create User Account]
    G --> H[Generate & Send OTP]
    H --> I{OTP Verified?}
    I -- No --> J[Resend OTP] --> H
    I -- Yes --> K[Account Active]

    B -- Yes --> L[Login Page]
    K --> L
    L --> M[Enter Phone / Email]
    M --> N[Send OTP]
    N --> O{OTP Valid?}
    O -- No --> P[Invalid OTP] --> L
    O -- Yes --> Q[Log Login Event]
    Q --> R{Role?}

    R -- Farmer --> S1[Farmer Dashboard]
    R -- Extension Officer --> S2[Extension Officer Dashboard]
    R -- Researcher --> S3[Researcher Dashboard]
    R -- KALRO Admin --> S4[Admin Control Center]

    classDef reg fill:#F5A623,stroke:#8B5A00,color:#fff
    classDef auth fill:#7ED321,stroke:#3B6B00,color:#fff
    classDef role fill:#9013FE,stroke:#4A0A85,color:#fff
    class C,D,E,F,G,H,I,J,K reg
    class L,M,N,O,P,Q auth
    class R,S1,S2,S3,S4 role
```
## 3. Farmer Flow
```mermaid
flowchart TD
    A[Farmer Dashboard] --> B[My Farm Profile]
    A --> C[Register Farm & GPS]
    A --> D[My Advisories]
    A --> E[Submit Feedback]
    A --> F[Climate Alerts]

    C --> C1[Bulk CSV Import]
    C --> C2[GPS Mapping]

    D --> D1{Channel}
    D1 -- SMS --> D2[Receive via iShamba]
    D1 -- Selector --> D3[Receive via Selector Platform]
    D1 -- Web --> D4[View in Dashboard]

    D4 --> D5[See Explainable Reasoning]
    D5 --> D6[Feature Attributions]
    D5 --> D7[Physics Residuals]

    E --> E1[Rate Advisory]
    E --> E2[Report Outcome]
    E2 --> LOOP[(Feedback Loop to PINN)]
```
## 4. Extension Officer Flow
```mermaid
flowchart TD
    A[Extension Officer Dashboard] --> B[Farmer Registry]
    A --> C[Climate Alerts]
    A --> D[Advisory Review]
    A --> E[Field Visits]
    A --> F[Trials Oversight]

    B --> B1[View Farmers]
    B --> B2[Add / Edit Farmer]
    B --> B3[Bulk CSV Import]

    C --> C1[Drought Alerts]
    C --> C2[Flood Alerts]
    C --> C3[Forecasts]

    D --> D1[Approve Advisory]
    D --> D2[Request Changes]
    D --> D3[Dispatch via SMS]
```
## 5. Researcher Flow
```mermaid
flowchart TD
    A[Researcher Dashboard] --> B[Field Trials]
    A --> C[Soil & Nutrient Data]
    A --> D[Crop Catalog]
    A --> E[Analytics]
    A --> F[PINN Metrics]

    B --> B1[Create Trial]
    B --> B2[Treatments & Plots]
    B --> B3[Plot-Level Results]
    B --> B4[CSV Import]

    C --> C1[Soil Tests]
    C --> C2[Nutrient Profiles]
    C --> C3[Market Prices]

    E --> E1[Yield Analytics]
    E --> E2[Treatment Comparisons]

    F --> F1[Training Runs]
    F --> F2[Physics Residuals]
    F --> F3[Model Accuracy]
```
## 6. KALRO Admin Flow
```mermaid
flowchart TD
    A[Admin Control Center] --> B[Accounts]
    A --> C[Farmers]
    A --> D[Climate]
    A --> E[Soil]
    A --> F[Crops]
    A --> G[Trials]
    A --> H[PINN Engine]
    A --> I[Advisories]
    A --> J[Integrations]
    A --> K[Audit Logs]

    B --> B1[Users & Roles]
    B --> B2[OTP Management]
    B --> B3[Login Audit]

    C --> C1[Farmer Registry]
    C --> C2[Farms & GPS]
    C --> C3[Bulk Import]

    D --> D1[Weather Records]
    D --> D2[Forecasts]
    D --> D3[Alerts]
    D --> D4[KAOP Sync]

    E --> E1[Soil Tests]
    E --> E2[Nutrient Profiles]
    E --> E3[AgData Hub Sync]

    F --> F1[Crop Catalog]
    F --> F2[Growth Stages]
    F --> F3[Planting Calendars]
    F --> F4[PINN Parameters]

    G --> G1[Trials]
    G --> G2[Treatments]
    G --> G3[Plot Results]
    G --> G4[Analytics]

    H --> H1[PINN Models]
    H --> H2[Physics Constraints]
    H --> H3[Training Runs]
    H --> H4[Inference & Metrics]

    I --> I1[Generate Advisory]
    I --> I2[Approve]
    I --> I3[Deliver]
    I --> I4[Feedback Loop]

    J --> J1[Provider Configs]
    J --> J2[Sync Logs]
    J --> J3[Webhook Events]
    J --> J4[Provider Dashboards]

    classDef admin fill:#D0021B,stroke:#6B000D,color:#fff
    class A,B,C,D,E,F,G,H,I,J,K,B1,B2,B3,C1,C2,C3,D1,D2,D3,D4,E1,E2,E3,F1,F2,F3,F4,G1,G2,G3,G4,H1,H2,H3,H4,I1,I2,I3,I4,J1,J2,J3,J4 admin
```
## 7. PINN Engine Flow
```mermaid
flowchart TD
    A[Data Sources] --> A1[Climate Records]
    A --> A2[Soil Tests]
    A --> A3[Field Trials]
    A --> A4[Crop Parameters]

    A1 --> B[PINN Engine]
    A2 --> B
    A3 --> B
    A4 --> B

    B --> C[Physics Constraints]
    C --> C1[Water Balance]
    C --> C2[Nutrient Cycling]
    C --> C3[Energy Conservation]

    C --> D[Loss Function]
    D --> E[Training Runs]
    E --> F[Model Metrics]
    F --> G[Inference]

    G --> H[Advisory Generation]
    H --> I[Feature Attributions]
    H --> J[Physics Residuals]
    H --> K[Explainability Output]

    K --> L[Advisory Approval]
    L --> M[Delivery: SMS / Selector / Web]
    M --> N[Farmer Feedback]
    N --> O[(Feedback Loop)]
    O --> B

    classDef data fill:#4A90E2,stroke:#1F3A5F,color:#fff
    classDef engine fill:#D0021B,stroke:#6B000D,color:#fff
    classDef physics fill:#9013FE,stroke:#4A0A85,color:#fff
    classDef output fill:#F5A623,stroke:#8B5A00,color:#fff
    class A,A1,A2,A3,A4 data
    class B,D,E,F,G,H engine
    class C,C1,C2,C3,I,J,K physics
    class L,M,N,O output
```
## 8. Advisory Lifecycle (Sequence)
```mermaid
sequenceDiagram
    participant F as Farmer
    participant E as Extension Officer
    participant P as PINN Engine
    participant A as KALRO Admin
    participant S as SMS / Selector

    F->>P: Farm data + GPS
    P->>P: Run inference
    P->>P: Apply physics constraints
    P->>A: Generate advisory + explainability
    A->>E: Send for review
    E->>A: Approve / Request changes
    A->>S: Dispatch advisory
    S->>F: Deliver (SMS ≤320 chars)
    F->>P: Submit feedback
    P->>P: Update model (feedback loop)
```
## 9. Integrations Flow
```mermaid
flowchart LR
    subgraph KALRO Advisory
        CORE[Core Platform]
    end

    subgraph External Systems
        KAOP[KAOP]
        AGDATA[AgData Hub]
        SELECTOR[Selector Platform]
        ISHAMBA[iShamba SMS]
    end

    CORE <-->|Sync| KAOP
    CORE <-->|Sync| AGDATA
    CORE <-->|Advisory Delivery| SELECTOR
    CORE <-->|SMS Delivery| ISHAMBA

    CORE --> LOGS[(Sync Logs)]
    CORE --> HOOKS[(Webhook Events)]
    CORE --> CONFIGS[(Provider Configs)]
```
## 10. Module Architecture
```mermaid
flowchart TD
    CORE[Django 6 Project] --> M1[accounts]
    CORE --> M2[farmers]
    CORE --> M3[climate]
    CORE --> M4[soil]
    CORE --> M5[crops]
    CORE --> M6[trials]
    CORE --> M7[pinn_engine]
    CORE --> M8[advisories]
    CORE --> M9[integrations]

    M1 --> R1[Custom User, 5 Roles, OTP, Login Audit]
    M2 --> R2[Farmer Registry, Farms, GPS, CSV Import]
    M3 --> R3[Weather, Forecasts, Alerts, KAOP Sync]
    M4 --> R4[Soil Tests, Nutrients, Prices, AgData Hub]
    M5 --> R5[Crop Catalog, Stages, Calendars, PINN Params]
    M6 --> R6[Trials, Treatments, Plot Results, Analytics]
    M7 --> R7[Models, Physics Constraints, Training, Inference]
    M8 --> R8[Generation, Approval, Delivery, Feedback]
    M9 --> R9[Providers, Sync Logs, Webhooks, Dashboards]
```
## 11. Permission Matrix
```mermaid
flowchart LR
    subgraph Roles
        FA[Farmer]
        EO[Extension Officer]
        RE[Researcher]
        AD[KALRO Admin]
    end

    subgraph Permissions
        P1[View Own Advisories]
        P2[Manage Farmers]
        P3[Approve Advisories]
        P4[Run Trials]
        P5[PINN Training]
        P6[Full CRUD All Modules]
        P7[Manage Integrations]
    end

    FA --> P1
    EO --> P1 & P2 & P3
    RE --> P1 & P4 & P5
    AD --> P1 & P2 & P3 & P4 & P5 & P6 & P7
```

---

## Features

### Core platform
- **Role-based dashboards** for Farmers, Extension Officers, Researchers, and KALRO Admins
- **Public landing page** with live stats pulled from the database
- **Full CRUD** for every module via the admin Control Center — inline, no navigation away
- **Explainable reasoning** — feature attributions and physics residuals shown per advisory
- **SMS-ready** advisory text (≤ 320 chars) and delivery logging

### Modules
| Module | Purpose |
|--------|---------|
| `accounts` | Custom User model with 5 roles, OTP, login audit |
| `farmers` | Farmer registry, farms, GPS mapping, bulk CSV import |
| `climate` | Weather records, forecasts, drought / flood alerts, KAOP sync |
| `soil` | Soil tests, nutrient profiles, market prices, AgData Hub sync |
| `crops` | Crop catalog, growth stages, planting calendars, PINN parameters |
| `trials` | Field trials, treatments, plot-level results, analytics, CSV import |
| `pinn_engine` | PINN models, physics constraints, training runs, inference, metrics |
| `advisories` | Advisory generation, approval, delivery, feedback loop |
| `integrations` | Provider configs, sync logs, webhook events, per-provider dashboards |

---

## Tech Stack

- **Backend:** Django 6.0, Django REST Framework
- **Database:** SQLite (development) · PostgreSQL (production)
- **AI:** Physics-Informed Neural Network (PINN) — inference via background tasks
- **Task queue:** Celery + Redis (production); synchronous fallback in dev
- **Frontend:** Django templates · Bootstrap 5 · Chart.js · Leaflet
- **Static files:** WhiteNoise
- **Deployment:** Render (blueprint in `render.yaml`)

---

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/eKidenge/kalro_advisory.git
cd kalro_advisory

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

Create `.env` in the project root:

```
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@kalro.go.ke
DJANGO_SUPERUSER_PASSWORD=admin123
```

### 3. Migrate and seed

```bash
python manage.py migrate
python load_data.py
```

`load_data.py` seeds:
- 47 Kenyan counties
- 7 crop categories
- 20 common Kenyan crops
- 3 baseline physics constraints
- A superuser (from the `DJANGO_SUPERUSER_*` env vars)

### 4. Run

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

---

## Role-Based Access

| Role | Dashboard | Access |
|------|-----------|--------|
| **Farmer** | Own advisories & farm profile | Own data only |
| **Extension Officer** | County field data | Farmers, farms, soil, climate in their county |
| **Researcher** | Analytics, PINN models, trials | Nationwide read + model training |
| **KALRO Admin** | Full Control Center | Everything — user management, integrations, approvals |
| **System Admin** | Same as KALRO Admin | Superuser access |

---

## Deployment (Render)

The repository ships with `render.yaml` and `build.sh`.

1. Push to GitHub
2. Render dashboard → **New +** → **Blueprint**
3. Connect the repo → Render creates:
   - A web service (`kalro-advisory`)
   - A PostgreSQL database (`kalro-db`)
4. Set the secret env var in the Render dashboard:
   - `DJANGO_SUPERUSER_PASSWORD` — your chosen admin password
5. Click **Deploy**

First build: installs deps, migrates, collects static, creates the superuser.

---

## Project Structure

```
kalro_advisory/
├── kalro_advisory/         # project settings, urls, wsgi/asgi
├── apps/
│   ├── accounts/           # users, roles, auth, permissions
│   ├── farmers/            # farmers, farms, counties
│   ├── climate/            # weather, forecasts, alerts
│   ├── soil/               # soil tests, nutrient profiles, market prices
│   ├── crops/              # crops, growth stages, calendars
│   ├── trials/             # field trials, results, analytics
│   ├── pinn_engine/        # PINN models, physics, training, inference
│   ├── advisories/         # advisories, delivery, feedback
│   └── integrations/       # KAOP, AgData, Selector, iShamba
├── templates/              # project-wide templates
├── static/                 # CSS, JS, images
├── build.sh                # Render build script
├── render.yaml             # Render blueprint
├── requirements.txt
├── load_data.py            # Seed script
└── manage.py
```

---

## Roadmap

- [x] Django project, 9 apps, 100+ templates
- [x] Role-based auth, permissions, dashboards
- [x] Admin Control Center with inline CRUD for every module
- [x] Landing page with live DB stats
- [x] Production-ready settings (Postgres, WhiteNoise, security)
- [ ] Real PINN model training pipeline
- [ ] KAOP, AgData Hub, Selector, iShamba real API clients
- [ ] Celery + Redis background task queue
- [ ] REST API for mobile clients
- [ ] Full test coverage

---

## License

Proprietary — © Kenya Agricultural and Livestock Research Organization (KALRO).
All rights reserved.

---

## Contact

- **Repository:** https://github.com/eKidenge/kalro_advisory
- **Organization:** Kenya Agricultural and Livestock Research Organization
- **Email:** admin@kalro.go.ke
