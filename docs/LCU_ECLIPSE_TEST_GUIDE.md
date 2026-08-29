# LCU: ECLIPSE — EVENT ORGANIZER MASTER TEST GUIDE & WALKTHROUGH

> [!CAUTION]
> **CONFIDENTIAL: ORGANIZER ONLY — DO NOT SHOW PARTICIPANTS**
> This document contains solutions, decryption keys, solving SQL queries, and vulnerability test cases for the **MURDER MYSTIQL: LCU ECLIPSE** investigation challenge (Invente 2026). Keep this file internal to the organizing team.

---

## 1. Investigation Overview & Architecture

- **Story**: LCU: ECLIPSE (10-level sequential mystery)
- **Database Engine**: PostgreSQL / Supabase
- **Authentication**: Firebase Authentication (Institutional `@ssn.edu.in` domain required, `email_verified == true`)
- **Qualification**: 5-question SQL/Logic quiz (Qualifying score: 3/5)
- **Scoring**: Effective Investigation Time = `Elapsed Time + Hint Penalties (+2m each) + Wrong Answer Penalties (+5m each)`
- **Lockout**: 60-second submission lockout after any incorrect answer
- **Security**: Strict read-only SQL execution sandboxing (`SELECT` / `WITH` only; blocked mutations and protected tables)

---

## 2. Level-by-Level Solution Manual

### Level 1: The Ghost Shipment at Ennore

- **Level Number**: 1
- **Level Title**: The Ghost Shipment at Ennore
- **Story Context**: On March 14, 2024 at 02:40 IST, a dark green Ashok Leyland truck (`TN-04-E-8819`) entered Ennore Port CFS-4. The cargo was declared as industrial machinery consigned to Scorpion Maritime Logistics, but secretly concealed 12 cylinders of Compound-9 precursor.
- **Objective**: What is the container tracking number of the suspicious shipment that cleared Ennore Port CFS-4?
- **Clue Shown to Participant**: Filter the `shipments` table for shipments arriving at Ennore Port with a declared manifest of Industrial Machinery.
- **Tables Available**: `shipments`, `locations`
- **SQL Concept Tested**: Basic `SELECT` projection and `WHERE` filtering with text pattern matching (`LIKE` / `ILIKE`).
- **Solving SQL Query**:
  ```sql
  SELECT container_number, declared_manifest, destination, clearance_status
  FROM shipments
  WHERE destination LIKE '%Ennore%'
    AND declared_manifest ILIKE '%Industrial Machinery%';
  ```
- **Expected Query Result**:
  | container_number | declared_manifest | destination | clearance_status |
  | :--- | :--- | :--- | :--- |
  | `MEDU-774910-2` | Industrial Machinery - Lathe Spindles | Ennore Port CFS-4 | CLEARED_BYPASS |
- **Correct Answer**: `MEDU-774910-2`
- **Unlocked Tables**: `access_logs`, `vehicle_records`
- **Hint**: `SELECT container_number FROM shipments WHERE destination LIKE '%Ennore%' AND declared_manifest LIKE '%Industrial%';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second submission lockout)
- **Red Herring**: Shipment `MEDU-441209-1` at Ennore carrying `Automobile Components` with clearance `CLEARED_INSPECTED`.
- **Organizer Verification**: Confirm query returns 1 matching row with `MEDU-774910-2` and submitting unlocks Level 2 and Level 2 tables.

---

### Level 2: The Security Breach & Customs Bypass

- **Level Number**: 2
- **Level Title**: The Security Breach & Customs Bypass
- **Story Context**: Customs bypass logs show that Terminal Gate 7 was breached using an unauthorized override code right before truck `TN-04-E-8819` cleared the checkpoint without physical inspection.
- **Objective**: What biometric override ID or badge was used to bypass the Gate 7 boom barrier at Ennore Port?
- **Clue Shown to Participant**: Check `access_logs` for security events occurring at Gate 7 on 2024-03-14 around 02:35 IST.
- **Tables Available**: `shipments`, `locations`, `access_logs`, `vehicle_records`
- **SQL Concept Tested**: Multi-condition filtering (`WHERE ... AND ...`) and timestamp inspection.
- **Solving SQL Query**:
  ```sql
  SELECT log_id, card_or_badge_id, user_name, facility_location, access_timestamp, action_description
  FROM access_logs
  WHERE facility_location LIKE '%Gate 7%'
    AND action_description LIKE '%Override%'
  ORDER BY access_timestamp DESC;
  ```
- **Expected Query Result**:
  | card_or_badge_id | user_name | facility_location | action_description |
  | :--- | :--- | :--- | :--- |
  | `ADMIN-01` | SYSTEM_OVERRIDE_ROOT | Ennore Port - Gate 7 Barrier | Manual emergency barrier override executed - Inspection bypassed |
- **Correct Answer**: `ADMIN-01`
- **Unlocked Tables**: `phone_records`
- **Hint**: `SELECT card_or_badge_id, action_description FROM access_logs WHERE facility_location LIKE '%Gate 7%' AND access_timestamp::text LIKE '2024-03-14%';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Routine badge `SEC-8812` swiped at 02:10 for regular perimeter patrol.
- **Organizer Verification**: Verify `ADMIN-01` unlocks Level 3 and the `phone_records` table.

---

### Level 3: Intercepting the Command Call

- **Level Number**: 3
- **Level Title**: Intercepting the Command Call
- **Story Context**: Upon receiving the Compound-9 precursor, Rolex placed an encrypted call to his northern strike unit in Shimla ordering an immediate hit on Parthiban / Leo Das.
- **Objective**: What caller IMSI placed the directive call from the Ennore-North cell tower at 03:15 IST on March 14, 2024?
- **Clue Shown to Participant**: Query the `phone_records` table for the caller_imsi connected to cell tower "Ennore-North" at 03:15.
- **Tables Available**: `shipments`, `locations`, `access_logs`, `vehicle_records`, `phone_records`
- **SQL Concept Tested**: Filtering cellular call records by tower identifier and timestamp strings.
- **Solving SQL Query**:
  ```sql
  SELECT call_id, caller_imsi, receiver_imsi, caller_name, cell_tower, call_timestamp, notes
  FROM phone_records
  WHERE cell_tower = 'Ennore-North'
    AND call_timestamp::text LIKE '2024-03-14 03:15%';
  ```
- **Expected Query Result**:
  | caller_imsi | receiver_imsi | caller_name | cell_tower | notes |
  | :--- | :--- | :--- | :--- | :--- |
  | `404-45-89102482` | 404-45-77219003 | [UNKNOWN_BURNOUT] | Ennore-North | Encrypted satellite relay to Shimla Sector |
- **Correct Answer**: `404-45-89102482`
- **Unlocked Tables**: `bank_transactions`, `messages`
- **Hint**: `SELECT caller_imsi, notes FROM phone_records WHERE cell_tower = 'Ennore-North' AND call_timestamp::text LIKE '2024-03-14 03:15%';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Routine worker voice call `404-45-11002233` from Ennore-South tower.
- **Organizer Verification**: Confirm `404-45-89102482` unlocks Level 4 and `bank_transactions`, `messages`.

---

### Level 4: The Corrupt Deputy in Theog

- **Level Number**: 4
- **Level Title**: The Corrupt Deputy in Theog
- **Story Context**: To track down Parthiban in Theog, Rolex routed a massive bribe via Scorpion Maritime Corp in Panama to a corrupt local deputy inspector in Shimla.
- **Objective**: What is the name of the recipient account holder who received a ₹50,00,000 wire transfer from Scorpion Maritime Corp?
- **Clue Shown to Participant**: Inspect `bank_transactions` for a wire transfer of ₹50,00,000 sent by Scorpion Maritime Corp.
- **Tables Available**: `shipments`, `locations`, `access_logs`, `vehicle_records`, `phone_records`, `bank_transactions`, `messages`
- **SQL Concept Tested**: Exact numeric amount matching (`amount = 5000000`) and substring text search.
- **Solving SQL Query**:
  ```sql
  SELECT transaction_id, sender_account, receiver_account, amount, reference_number, transaction_timestamp
  FROM bank_transactions
  WHERE sender_account LIKE '%Scorpion Maritime%'
    AND amount = 5000000;
  ```
- **Expected Query Result**:
  | sender_account | receiver_account | amount | reference_number |
  | :--- | :--- | :--- | :--- |
  | Scorpion Maritime Corp (Panama) | Sanjeev Kumar (Deputy Inspector) | 5000000.00 | WIRE-PAN-902148 |
- **Correct Answer**: `Sanjeev Kumar`
- **Unlocked Tables**: `evidence`
- **Hint**: `SELECT receiver_account, amount, reference_number FROM bank_transactions WHERE sender_account LIKE '%Scorpion Maritime%' AND amount = 5000000;`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Small logistics vendor transfers (< ₹2,00,000) to port suppliers.
- **Organizer Verification**: Confirm `Sanjeev Kumar` unlocks Level 5 and the `evidence` table.

---

### Level 5: The Ambush at Nellore Yard

- **Level Number**: 5
- **Level Title**: The Ambush at Nellore Yard
- **Story Context**: On March 18, 2024, Anbu led a hit team to the Nellore Agricultural Checkpost to interrogate Dilli about the 2019 transit ledger. Dilli dismantled the squad and damaged their vehicle before contacting Vikram.
- **Objective**: What was the vehicle registration plate of the black Mahindra Scorpio used in the Nellore ambush?
- **Clue Shown to Participant**: Look at `vehicle_records` for a black Scorpio sighted at the Nellore Highway on 2024-03-18.
- **Tables Available**: `shipments`, `locations`, `access_logs`, `vehicle_records`, `phone_records`, `bank_transactions`, `messages`, `evidence`
- **SQL Concept Tested**: Multi-column text filtering on geographic location and vehicle model.
- **Solving SQL Query**:
  ```sql
  SELECT registration_number, vehicle_type, registered_owner, sighting_location, sighting_timestamp
  FROM vehicle_records
  WHERE sighting_location LIKE '%Nellore%'
    AND vehicle_type LIKE '%Scorpio%';
  ```
- **Expected Query Result**:
  | registration_number | vehicle_type | registered_owner | sighting_location |
  | :--- | :--- | :--- | :--- |
  | `AP-26-BK-9009` | Mahindra Scorpio (Black) | Kada Syndicate Front Ltd | Nellore Highway Checkpost Km 42 |
- **Correct Answer**: `AP-26-BK-9009`
- **Unlocked Tables**: `characters`, `relationships`
- **Hint**: `SELECT registration_number, vehicle_type, registered_owner FROM vehicle_records WHERE sighting_location LIKE '%Nellore%';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Transport lorry `AP-26-TT-1102` sighted near the toll plaza at 14:00.
- **Organizer Verification**: Confirm `AP-26-BK-9009` unlocks Level 6 and `characters`, `relationships`.

---

### Level 6: The State Intelligence Mole

- **Level Number**: 6
- **Level Title**: The State Intelligence Mole
- **Story Context**: When Leo Das, Dilli, Vikram, Amar, and Napoleon converged at the Ranipet Ceramic Factory, their coordinates were leaked to Rolex by a high-ranking mole in the State OCIU.
- **Objective**: Which corrupt intelligence officer leaked the Ranipet safehouse coordinates via message at 23:50 IST on 2024-04-04?
- **Clue Shown to Participant**: Check the `messages` table for transmissions mentioning Ranipet on 2024-04-04, and cross-reference with `access_logs` or `characters`.
- **Tables Available**: `shipments`, `locations`, `access_logs`, `vehicle_records`, `phone_records`, `bank_transactions`, `messages`, `evidence`, `characters`, `relationships`
- **SQL Concept Tested**: Relational JOIN between `messages` (intercepted SMS) and `phone_records` (cellular IMSI registrant).
- **Solving SQL Query**:
  ```sql
  SELECT m.sender, m.receiver, m.message_text, p.caller_name
  FROM messages m
  JOIN phone_records p ON p.caller_imsi = m.sender
  WHERE m.message_text LIKE '%Ranipet%'
    AND m.sent_timestamp::text LIKE '2024-04-04 23:50%';
  ```
- **Expected Query Result**:
  | sender | caller_name | message_text |
  | :--- | :--- | :--- |
  | `404-22-77610293` | `ACP Stephen Raj` | Target is in Ranipet Tile Works. 5 men inside. Close the perimeter now. |
- **Correct Answer**: `ACP Stephen Raj`
- **Unlocked Tables**: `timeline_events`
- **Hint**: `SELECT m.sender, m.message_text, p.caller_name FROM messages m JOIN phone_records p ON p.caller_imsi = m.sender WHERE m.message_text LIKE '%Ranipet%';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Routine status dispatch from Special Branch Officer Jose.
- **Organizer Verification**: Confirm `ACP Stephen Raj` unlocks Level 7 and `timeline_events`.

---

### Level 7: The Hawala Trail

- **Level Number**: 7
- **Level Title**: The Hawala Trail
- **Story Context**: A massive hawala payment was wired through Dubai to reward Stephen Raj for delivering the Ranipet safehouse coordinates.
- **Objective**: What was the unique reference number of the ₹2,00,00,000 hawala payout transferred to account SR-77?
- **Clue Shown to Participant**: Query `bank_transactions` for the ₹2,00,00,000 transfer to receiver account SR-77.
- **Tables Available**: All previous tables through `timeline_events`
- **SQL Concept Tested**: Filter on high-value transaction (`amount = 20000000`) and receiver account code.
- **Solving SQL Query**:
  ```sql
  SELECT transaction_id, sender_account, receiver_account, amount, reference_number, transaction_type
  FROM bank_transactions
  WHERE receiver_account LIKE '%SR-77%'
    AND amount = 20000000;
  ```
- **Expected Query Result**:
  | sender_account | receiver_account | amount | reference_number |
  | :--- | :--- | :--- | :--- |
  | Al-Rashid Global Trading LLC (Dubai) | SR-77 (Hawala Disbursal Node) | 20000000.00 | `HWL-DXB-44102` |
- **Correct Answer**: `HWL-DXB-44102`
- **Unlocked Tables**: `red_herrings`, `autopsies`
- **Hint**: `SELECT reference_number FROM bank_transactions WHERE receiver_account LIKE '%SR-77%' AND amount = 20000000;`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Domestic payment of ₹15,00,000 to account `SR-12`.
- **Organizer Verification**: Confirm `HWL-DXB-44102` unlocks Level 8 and `red_herrings`, `autopsies`.

---

### Level 8: The Siege of Ranipet & Cartel Executions

- **Level Number**: 8
- **Level Title**: The Siege of Ranipet & Cartel Executions
- **Story Context**: During the siege of the ceramic factory on April 5, 2024, Leo Das cornered Viper Selvam in the boiler room to extract the landing coordinates of the master synthesis lab.
- **Objective**: What was the exact forensic cause of death / lethal method used on Viper Selvam in the Ranipet boiler room?
- **Clue Shown to Participant**: Query the `autopsies` or `evidence` table for the cause_of_death of Viper Selvam.
- **Tables Available**: All previous tables through `autopsies` and `red_herrings`
- **SQL Concept Tested**: Record lookup in `autopsies` table filtering by `victim_name`.
- **Solving SQL Query**:
  ```sql
  SELECT autopsy_id, victim_name, time_of_death, location_found, cause_of_death, killer_name
  FROM autopsies
  WHERE victim_name = 'Viper Selvam';
  ```
- **Expected Query Result**:
  | victim_name | location_found | cause_of_death | killer_name |
  | :--- | :--- | :--- | :--- |
  | Viper Selvam | Ranipet Ceramic Factory - Boiler Room | `Manual Cervical Dislocation` | Leo Das |
- **Correct Answer**: `Manual Cervical Dislocation`
- **Unlocked Tables**: `kill_records`
- **Hint**: `SELECT victim_name, cause_of_death, killer_name FROM autopsies WHERE victim_name = 'Viper Selvam';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Gunshot trauma sustained by peripheral henchmen in the outer perimeter.
- **Organizer Verification**: Confirm `Manual Cervical Dislocation` unlocks Level 9 and `kill_records`.

---

### Level 9: The Floating Refinery at Royapuram

- **Level Number**: 9
- **Level Title**: The Floating Refinery at Royapuram
- **Story Context**: Selvam confessed that Rolex was personally inspecting the narcotics synthesis conversion lab aboard a container ship berthed at Royapuram Coal Terminal Berth 11.
- **Objective**: What is the International Maritime Organization (IMO) vessel identification number of the ship MV Scorpia?
- **Clue Shown to Participant**: Query the `shipments` table for the imo_number of the vessel MV Scorpia.
- **Tables Available**: All tables through `kill_records`
- **SQL Concept Tested**: Querying maritime vessel metadata (`imo_number`) from `shipments`.
- **Solving SQL Query**:
  ```sql
  SELECT shipment_id, vessel_name, imo_number, destination, actual_cargo
  FROM shipments
  WHERE vessel_name = 'MV Scorpia';
  ```
- **Expected Query Result**:
  | vessel_name | imo_number | destination | actual_cargo |
  | :--- | :--- | :--- | :--- |
  | MV Scorpia | `9182344` | Royapuram Coal Terminal Berth 11 | Compound-9 Master Synthesis Mobile Rig |
- **Correct Answer**: `9182344`
- **Unlocked Tables**: Full schema access (Level 10)
- **Hint**: `SELECT imo_number FROM shipments WHERE vessel_name = 'MV Scorpia';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Standard cargo vessel `MV Chennai Trader` with IMO `9241801`.
- **Organizer Verification**: Confirm `9182344` advances to Level 10.

---

### Level 10: The Apex Execution & Final Deduction

- **Level Number**: 10
- **Level Title**: The Apex Execution & Final Deduction
- **Story Context**: On April 6, 2024 at 03:18 IST, the final showdown occurred inside the MV Scorpia central laboratory hold. The supreme kingpin was eliminated, terminating the Das & Co drug legacy forever.
- **Objective**: Who killed Rolex, and what weapon was used? Format: `<Killer> - <Weapon>` (e.g. `Leo Das - Kukri`)
- **Clue Shown to Participant**: Query the `autopsies` or `kill_records` table to identify the killer and weapon associated with victim Rolex.
- **Tables Available**: All 14 investigation tables
- **SQL Concept Tested**: Relational synthesis between `kill_records` and `autopsies` for definitive deduction.
- **Solving SQL Query**:
  ```sql
  SELECT k.victim, k.killer, k.weapon, k.location, k.plot_impact, a.cause_of_death
  FROM kill_records k
  JOIN autopsies a ON a.victim_name = k.victim
  WHERE k.victim = 'Rolex';
  ```
- **Expected Query Result**:
  | victim | killer | weapon | location | cause_of_death |
  | :--- | :--- | :--- | :--- | :--- |
  | Rolex | Leo Das | Kukri | MV Scorpia Central Lab Hold | Decapitation via Kukri Blade |
- **Correct Answer**: `Leo Das - Kukri`
- **Unlocked Tables**: Investigation Completed
- **Hint**: `SELECT killer_name, cause_of_death FROM autopsies WHERE victim_name = 'Rolex';`
- **Hint Penalty**: +2 minutes
- **Wrong Answer Penalty**: +5 minutes (plus 60-second lockout)
- **Red Herring**: Speculation that Amar or Vikram delivered the fatal blow.
- **Organizer Verification**: Submitting `Leo Das - Kukri` completes the investigation, stops the server timer, sets session status to `COMPLETED`, and publishes the final effective time to the Leaderboard.

---

## 3. Complete End-to-End Organizer Walkthrough

Organizers should perform this complete sequence on a staging or test deployment:

```
[START]
   │
   ▼
1. Sign In with Google
   └── Use verified institutional account (e.g. detective@ssn.edu.in)
   │
   ▼
2. Qualification Quiz (5 Questions)
   └── Submit valid answers (requires >= 3/5 correct to qualify)
   │
   ▼
3. Enter Investigation Terminal (Level 1)
   └── View story prologue and mission dossier
   └── Inspect available tables (shipments, locations)
   └── Run Level 1 query: SELECT container_number FROM shipments WHERE destination LIKE '%Ennore%';
   └── Submit: MEDU-774910-2
   │
   ▼
4. Advance through Levels 2–9
   └── Level 2: ADMIN-01
   └── Level 3: 404-45-89102482
   └── Level 4: Sanjeev Kumar
   └── Level 5: AP-26-BK-9009
   └── Level 6: ACP Stephen Raj
   └── Level 7: HWL-DXB-44102
   └── Level 8: Manual Cervical Dislocation
   └── Level 9: 9182344
   │
   ▼
5. Final Level 10 Showdown
   └── Submit: Leo Das - Kukri
   │
   ▼
6. Completion & Leaderboard
   └── Session marked 'COMPLETED'
   └── Verify team rank, elapsed time, and applied penalty breakdown on /api/leaderboard
```

---

## 4. Organizer Bug Hunt & Security Checklist

When testing before the live event, verify each item against the expected secure behavior:

| # | Test Scenario | Steps to Execute | Expected Secure Behavior |
| :--- | :--- | :--- | :--- |
| **1** | **Direct API without Token** | Send `POST /api/query/execute` or `POST /api/game/start` with no `Authorization` header | Returns `401 Unauthorized`. Request rejected. |
| **2** | **Non-SSN Domain** | Attempt sign-in with `@gmail.com` or `@yahoo.com` Google account | Returns `403 Forbidden` (`Only verified SSN institutional accounts (@ssn.edu.in) can participate`). |
| **3** | **Domain Spoofing Attack** | Attempt token with email `hacker@ssn.edu.in.fake.com` | Returns `403 Forbidden` (`Only verified SSN institutional accounts (@ssn.edu.in) can participate`). |
| **4** | **Unverified Email** | Attempt token where `email_verified == false` | Returns `403 Forbidden` (`Email address must be verified`). |
| **5** | **SQL Mutation Attempt** | Execute `DROP TABLE shipments;`, `DELETE FROM access_logs;`, `INSERT INTO shipments ...;` | Returns `403 Forbidden` (`Only read-only SELECT and WITH queries are allowed`). |
| **6** | **Protected Table Query** | Execute `SELECT * FROM game_levels;` or `SELECT * FROM answer_submissions;` | Returns `403 Forbidden` (`Access to system or game configuration table ... is prohibited`). |
| **7** | **Locked Table Query** | Execute `SELECT * FROM autopsies;` while at Level 1 | Returns `403 Forbidden` (`Table 'autopsies' is locked. Unlocks at Level 8`). |
| **8** | **Wrong Answer Submission** | Submit incorrect answer string on any level | Returns `correct: false`, adds `+300s` (+5m) penalty to session, initiates 60s lockout. |
| **9** | **Lockout Enforcement** | Submit another answer immediately during the 60s lockout window | Returns `429 Too Many Requests` (`Lockout active. Please wait X more seconds before submitting again`). |
| **10** | **Hint Usage Penalty** | Click "Unlock Hint" on an active level | Returns hint text and adds `+120s` (+2m) hint penalty to effective time. |
| **11** | **Browser Refresh** | Refresh the browser during an active level | Session state, current level, elapsed timer, and unlocked tables persist automatically from server. |
| **12** | **Sign Out / Sign In** | Sign out and sign back in with the same `@ssn.edu.in` account | The exact same session and timer are restored; no duplicate session or timer reset occurs. |
| **13** | **Multi-Tab Concurrency** | Open game in two browser tabs with the same account | Actions in one tab reflect in the session without desynchronization. |
| **14** | **Client-Side Timer Tampering** | Attempt to modify client-side timer variables in DevTools | Timer and effective duration are calculated strictly on the server (`server-authoritative`). |
| **15** | **Query Row Limit** | Run `SELECT * FROM shipments;` | Results are capped cleanly at `max_query_rows` (200) without crashing the server. |

---

## 5. Summary of Seeded Level Answers

| Level | Title | Seeded Master Answer |
| :---: | :--- | :--- |
| **1** | The Ghost Shipment at Ennore | `MEDU-774910-2` |
| **2** | The Security Breach & Customs Bypass | `ADMIN-01` |
| **3** | Intercepting the Command Call | `404-45-89102482` |
| **4** | The Corrupt Deputy in Theog | `Sanjeev Kumar` |
| **5** | The Ambush at Nellore Yard | `AP-26-BK-9009` |
| **6** | The State Intelligence Mole | `ACP Stephen Raj` |
| **7** | The Hawala Trail | `HWL-DXB-44102` |
| **8** | The Siege of Ranipet & Cartel Executions | `Manual Cervical Dislocation` |
| **9** | The Floating Refinery at Royapuram | `9182344` |
| **10** | The Apex Execution & Final Deduction | `Leo Das - Kukri` |
