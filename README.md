# MURDER MYSTIQL: LCU ECLIPSE — Invente 2026

**MURDER MYSTIQL** is an interactive, data-driven SQL murder mystery investigation platform built for the **Invente 2026** competition. Participants play as shadow intelligence detectives querying relational databases to unravel a high-stakes conspiracy.

> **DISCLAIMER: FAN-MADE FICTION**  
> *LCU: ECLIPSE* is a work of fan fiction created for entertainment and mystery-game purposes. It is **not** official canon of the Lokesh Cinematic Universe (LCU) or its respective production banners.

---

## 1. System Architecture

- **Frontend**: React 18, Vite, TypeScript, Lucide Icons, Custom Dark Investigative CSS Design.
- **Backend**: FastAPI (Python 3.10+), Pydantic v2, AsyncPG / PgBouncer connection pooler.
- **Database**: Supabase PostgreSQL with dedicated schemas:
  - `public`: Event configuration, levels, clues, hints, sessions, answer submissions, query logs, leaderboard view, and quiz shortlisting.
  - `investigation`: Port shipments, security access logs, vehicle sightings, phone intercepts, encrypted messages, bank/hawala transactions, forensic evidence, autopsies, and suspect dossiers.

---

## 2. Investigation Case: LCU: ECLIPSE

The case spans 10 progressive investigation levels:

1. **Level 01: The Ghost Shipment at Ennore** — Identify the container tracking number of the Compound-9 precursor entering Gate 7 (`shipments`).
2. **Level 02: The Security Breach & Customs Bypass** — Uncover the biometric override ID used to bypass the boom barrier (`access_logs`).
3. **Level 03: Intercepting the Command Call** — Find the caller IMSI used by Rolex to place the directive call to the Shimla hit squad (`phone_records`).
4. **Level 04: The Corrupt Deputy in Theog** — Trace the ₹50,00,000 wire transfer from Scorpion Maritime in Panama to the corrupt deputy (`bank_transactions`).
5. **Level 05: The Ambush at Nellore Yard** — Discover the registration number of the black Scorpio used by Anbu's squad (`vehicle_records`).
6. **Level 06: The State Intelligence Mole** — Identify the compromised OCIU officer who leaked the Ranipet safehouse GPS (`messages`, `access_logs`).
7. **Level 07: The Hawala Trail** — Uncover the transaction reference of the ₹2,00,00,000 Dubai hawala payout to Stephen Raj (`bank_transactions`).
8. **Level 08: The Siege of Ranipet & Cartel Executions** — Extract the forensic cause of death and lethal method used on Viper Selvam (`autopsies`, `evidence`).
9. **Level 09: The Floating Refinery at Royapuram** — Find the IMO vessel identification number of the container ship *MV Scorpia* (`shipments`).
10. **Level 10: The Apex Execution & Final Deduction** — Relational deduction of who killed Rolex and the weapon used (`autopsies`, `kill_records`, `evidence`).

---

## 3. SQL Security & Table Progression

- **Strict Read-Only Execution**: Only `SELECT` and `WITH` statements are permitted. Mutations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, etc.) are blocked at the engine gatekeeper.
- **Server-Side Table Gatekeeping**: Tables unlock level-by-level (e.g., `phone_records` is locked at Level 1 and only unlocks at Level 3). Queries attempting to reference locked or administrative tables return `403 Forbidden`.
- **Protected Administrative Entities**: Answer keys, level configurations, and session records are strictly inaccessible from participant SQL queries.

---

## 4. Scoring & Penalty Rules

- **Effective Time Formula**:
  $$\text{Effective Time} = \text{Elapsed Duration} + \text{Wrong Answer Penalty (5m)} + \text{Hint Penalty (2m)}$$
- **Trial & Error**: Executing SQL queries does **not** incur any penalty.
- **Wrong Answer Lockout**: Submitting an incorrect answer adds $+5$ minutes and enforces a 60-second submission lockout.
- **Hint Penalties**: Requesting a tactical clue adds $+2$ minutes to the effective competition time.

---

## 5. Setup & Local Development

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- Supabase Project (PostgreSQL)

### Environment Variables
Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```

Configure your credentials:
```ini
APP_ENV=development
SESSION_SECRET=your-secure-session-secret

SUPABASE_URL=https://vtaqddbmdteiwsswnwlz.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_DATABASE_URL=postgresql://postgres.vtaqddbmdteiwsswnwlz:your-password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

### Database Migration & Seed
In your Supabase SQL Editor:
1. Run `database/schema.sql` to create all public tables, enums, views, and the `investigation` schema.
2. Run `database/seed_lcu_eclipse.sql` to seed the event, levels, clues, hints, quiz questions, and full investigation datasets.

### Running the Application

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Node Dependencies**:
   ```bash
   npm install
   ```

3. **Start Development Servers**:
   ```bash
   npm run dev
   ```
   Or run the backend and frontend separately:
   - Backend: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload`
   - Frontend: `npm run dev:frontend` (Runs on `http://localhost:5000`)

---

## 6. Running Tests

Run the comprehensive end-to-end investigation suite:
```bash
python -m pytest tests/test_investigation.py -v
```

This validates:
- Playthrough from Level 1 to Level 10
- Server-side locked table enforcement
- SQL mutation and injection prevention
- Hint unlock and penalty calculations
- Wrong answer lockout and score adjustments
- Live leaderboard calculations
- Preliminary DBMS/SQL Quiz evaluations