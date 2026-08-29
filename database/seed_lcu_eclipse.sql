-- MURDER MYSTIQL: LCU ECLIPSE
-- Seed migration script for Invente 2026.
-- Populates the public configuration, 10 levels, clues, hints, locked tables,
-- quiz shortlisting module, and the full investigation schema datasets.

-- 1. Create Event & Configuration
insert into public.events (id, slug, name, tagline, description, status)
values (
  'e0000000-0000-0000-0000-000000000001',
  'invente-2026',
  'MURDER MYSTIQL: LCU ECLIPSE',
  'Invente 2026 SQL Investigation Challenge',
  'A high-stakes relational SQL mystery set in the aftermath of the Das & Co collapse.',
  'live'
) on conflict (slug) do update set
  name = excluded.name,
  tagline = excluded.tagline,
  description = excluded.description,
  status = excluded.status;

insert into public.event_config (
  event_id,
  wrong_answer_penalty_minutes,
  wrong_answer_lock_seconds,
  hint_penalty_default_minutes,
  allow_pause,
  max_query_rows,
  query_timeout_ms,
  quiz_required,
  quiz_qualify_score
) values (
  'e0000000-0000-0000-0000-000000000001',
  5,
  60,
  2,
  false,
  200,
  3000,
  false,
  3
) on conflict (event_id) do update set
  wrong_answer_penalty_minutes = excluded.wrong_answer_penalty_minutes,
  wrong_answer_lock_seconds = excluded.wrong_answer_lock_seconds,
  hint_penalty_default_minutes = excluded.hint_penalty_default_minutes,
  quiz_required = excluded.quiz_required,
  quiz_qualify_score = excluded.quiz_qualify_score;

insert into public.stories (
  id,
  event_id,
  title,
  prologue,
  description,
  disclaimer,
  status
) values (
  'a0000000-0000-0000-0000-000000000001',
  'e0000000-0000-0000-0000-000000000001',
  'LCU: ECLIPSE',
  'The foundation of the South Indian narcotics corridor rests on three cataclysms: Trichy (2019), Chennai (2022), and Theog (2023). When a dormant 20-year automated maintenance protocol in Theog triggers a backdated shipment of Compound-9 to Ennore Port under Scorpion Maritime, Rolex discovers that Leo Das is alive and operating as Parthiban. A lethal war converges across Nellore, Ranipet, and Royapuram Port.',
  'A full relational investigation into the ghost shipments, intelligence leaks, and final showdown of the LCU Eclipse case.',
  'LCU: ECLIPSE is fan-made fiction created for entertainment and mystery-game purposes. It is not official canon of the Lokesh Cinematic Universe.',
  'live'
) on conflict (event_id) do update set
  title = excluded.title,
  prologue = excluded.prologue,
  description = excluded.description,
  disclaimer = excluded.disclaimer,
  status = excluded.status;

-- 2. Investigation Table Catalog (with column metadata)
delete from public.investigation_tables where event_id = 'e0000000-0000-0000-0000-000000000001';

insert into public.investigation_tables (id, event_id, table_name, display_label, schema_name, unlock_level, description, columns_metadata)
values
(
  'b0000000-0000-0000-0000-000000000001',
  'e0000000-0000-0000-0000-000000000001',
  'shipments',
  'Port Cargo Shipments',
  'investigation',
  1,
  'Customs manifest, vessels, origins, destinations, and declared vs actual cargo.',
  '[{"name":"shipment_id","data_type":"text","is_primary_key":true},{"name":"container_number","data_type":"text"},{"name":"vessel_name","data_type":"text"},{"name":"imo_number","data_type":"text"},{"name":"declared_manifest","data_type":"text"},{"name":"actual_cargo","data_type":"text"},{"name":"origin","data_type":"text"},{"name":"destination","data_type":"text"},{"name":"arrival_timestamp","data_type":"timestamptz"},{"name":"clearance_status","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000002',
  'e0000000-0000-0000-0000-000000000001',
  'locations',
  'Geographic Locations',
  'investigation',
  1,
  'Key operational hubs, coordinates, and tactical facilities.',
  '[{"name":"location_id","data_type":"text","is_primary_key":true},{"name":"name","data_type":"text"},{"name":"state","data_type":"text"},{"name":"latitude","data_type":"numeric(9,4)"},{"name":"longitude","data_type":"numeric(9,4)"},{"name":"description","data_type":"text"},{"name":"significance","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000003',
  'e0000000-0000-0000-0000-000000000001',
  'access_logs',
  'Facility Security Access Logs',
  'investigation',
  2,
  'Biometric overrides, badge swipes, and terminal security events.',
  '[{"name":"log_id","data_type":"text","is_primary_key":true},{"name":"card_or_badge_id","data_type":"text"},{"name":"user_name","data_type":"text"},{"name":"facility_location","data_type":"text"},{"name":"access_timestamp","data_type":"timestamptz"},{"name":"action_description","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000004',
  'e0000000-0000-0000-0000-000000000001',
  'vehicle_records',
  'Vehicle Sightings & Registration',
  'investigation',
  2,
  'Highway toll sightings, truck plates, and registered owner records.',
  '[{"name":"vehicle_id","data_type":"text","is_primary_key":true},{"name":"registration_number","data_type":"text"},{"name":"vehicle_type","data_type":"text"},{"name":"registered_owner","data_type":"text"},{"name":"sighting_location","data_type":"text"},{"name":"sighting_timestamp","data_type":"timestamptz"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000005',
  'e0000000-0000-0000-0000-000000000001',
  'phone_records',
  'Cellular Intercepts & Call Logs',
  'investigation',
  3,
  'IMSI intercepts, cell tower connections, durations, and call logs.',
  '[{"name":"call_id","data_type":"text","is_primary_key":true},{"name":"caller_imsi","data_type":"text"},{"name":"receiver_imsi","data_type":"text"},{"name":"caller_name","data_type":"text"},{"name":"receiver_name","data_type":"text"},{"name":"call_timestamp","data_type":"timestamptz"},{"name":"duration_seconds","data_type":"integer"},{"name":"cell_tower","data_type":"text"},{"name":"notes","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000006',
  'e0000000-0000-0000-0000-000000000001',
  'bank_transactions',
  'Financial & Hawala Transactions',
  'investigation',
  4,
  'Offshore wire transfers, hawala payouts, and cash withdrawals.',
  '[{"name":"transaction_id","data_type":"text","is_primary_key":true},{"name":"sender_account","data_type":"text"},{"name":"receiver_account","data_type":"text"},{"name":"amount","data_type":"numeric(14,2)"},{"name":"transaction_type","data_type":"text"},{"name":"reference_number","data_type":"text"},{"name":"transaction_timestamp","data_type":"timestamptz"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000007',
  'e0000000-0000-0000-0000-000000000001',
  'messages',
  'Decrypted Radio & SMS Transmissions',
  'investigation',
  4,
  'Field transmissions, leaking of coordinates, and directive orders.',
  '[{"name":"message_id","data_type":"text","is_primary_key":true},{"name":"sender","data_type":"text"},{"name":"receiver","data_type":"text"},{"name":"sent_timestamp","data_type":"timestamptz"},{"name":"message_text","data_type":"text"},{"name":"encryption_type","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000008',
  'e0000000-0000-0000-0000-000000000001',
  'evidence',
  'Forensics & Physical Ballistics',
  'investigation',
  5,
  'Weapons, spent casings, tools, and digital flash drives recovered.',
  '[{"name":"evidence_id","data_type":"text","is_primary_key":true},{"name":"item_name","data_type":"text"},{"name":"recovered_location","data_type":"text"},{"name":"recovery_timestamp","data_type":"timestamptz"},{"name":"forensic_summary","data_type":"text"},{"name":"matching_suspect","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000009',
  'e0000000-0000-0000-0000-000000000001',
  'characters',
  'Dossier of Suspects & Operatives',
  'investigation',
  6,
  'Operative aliases, affiliations, roles, and status.',
  '[{"name":"character_id","data_type":"text","is_primary_key":true},{"name":"full_name","data_type":"text"},{"name":"alias","data_type":"text"},{"name":"primary_role","data_type":"text"},{"name":"location_base","data_type":"text"},{"name":"organization","data_type":"text"},{"name":"status","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000010',
  'e0000000-0000-0000-0000-000000000001',
  'relationships',
  'Syndicate Ties & Kinship Matrix',
  'investigation',
  6,
  'Connections between leaders, family ties, and alliances.',
  '[{"name":"relationship_id","data_type":"text","is_primary_key":true},{"name":"person_a","data_type":"text"},{"name":"person_b","data_type":"text"},{"name":"relationship_type","data_type":"text"},{"name":"details","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000011',
  'e0000000-0000-0000-0000-000000000001',
  'timeline_events',
  'Master Incident Timeline',
  'investigation',
  7,
  'Chronological timeline of incidents from 2004 through Royapuram 2024.',
  '[{"name":"event_code","data_type":"text","is_primary_key":true},{"name":"occurred_at","data_type":"timestamptz"},{"name":"location_name","data_type":"text"},{"name":"title","data_type":"text"},{"name":"summary","data_type":"text"},{"name":"key_individuals","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000012',
  'e0000000-0000-0000-0000-000000000001',
  'red_herrings',
  'False Leads & Forged Intel Dossiers',
  'investigation',
  8,
  'Fabricated OCIU records, false leaks, and debunking evidence.',
  '[{"name":"record_id","data_type":"text","is_primary_key":true},{"name":"lead_code","data_type":"text"},{"name":"apparent_theory","data_type":"text"},{"name":"forensic_truth","data_type":"text"},{"name":"debunking_evidence","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000013',
  'e0000000-0000-0000-0000-000000000001',
  'autopsies',
  'Coroner Post-Mortem Reports',
  'investigation',
  8,
  'Post-mortem findings, causes of death, time of death, and recovered motives.',
  '[{"name":"autopsy_id","data_type":"text","is_primary_key":true},{"name":"victim_name","data_type":"text"},{"name":"time_of_death","data_type":"timestamptz"},{"name":"location_found","data_type":"text"},{"name":"cause_of_death","data_type":"text"},{"name":"killer_name","data_type":"text"},{"name":"motive","data_type":"text"}]'::jsonb
),
(
  'b0000000-0000-0000-0000-000000000014',
  'e0000000-0000-0000-0000-000000000001',
  'kill_records',
  'Final Fatal Confrontation Log',
  'investigation',
  9,
  'Who killed whom, lethal methods, exact locations, and plot impacts.',
  '[{"name":"record_id","data_type":"text","is_primary_key":true},{"name":"victim","data_type":"text"},{"name":"killer","data_type":"text"},{"name":"weapon","data_type":"text"},{"name":"date_time","data_type":"timestamptz"},{"name":"location","data_type":"text"},{"name":"plot_impact","data_type":"text"}]'::jsonb
);

-- 3. Game Levels (10 Levels)
delete from public.game_levels where event_id = 'e0000000-0000-0000-0000-000000000001';

insert into public.game_levels (
  id,
  event_id,
  level_number,
  title,
  narrative_context,
  objective,
  clue,
  answer_type,
  answer_values,
  active
) values
(
  'c0000000-0000-0000-0000-000000000001',
  'e0000000-0000-0000-0000-000000000001',
  1,
  'The Ghost Shipment at Ennore',
  'On March 14, 2024 at 02:40 IST, a dark green Ashok Leyland truck (TN-04-E-8819) entered Ennore Port CFS-4. The cargo was declared as industrial machinery consigned to Scorpion Maritime Logistics, but secretly concealed 12 cylinders of Compound-9 precursor.',
  'What is the container tracking number of the suspicious shipment that cleared Ennore Port CFS-4?',
  'Filter the shipments table for shipments arriving at Ennore Port with a declared manifest of Industrial Machinery.',
  'case_insensitive',
  '["MEDU-774910-2"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000002',
  'e0000000-0000-0000-0000-000000000001',
  2,
  'The Security Breach & Customs Bypass',
  'Customs bypass logs show that Terminal Gate 7 was breached using an unauthorized override code right before truck TN-04-E-8819 cleared the checkpoint without physical inspection.',
  'What biometric override ID or badge was used to bypass the Gate 7 boom barrier at Ennore Port?',
  'Check access_logs for security events occurring at Gate 7 on 2024-03-14 around 02:35 IST.',
  'case_insensitive',
  '["ADMIN-01"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000003',
  'e0000000-0000-0000-0000-000000000001',
  3,
  'Intercepting the Command Call',
  'Upon receiving the Compound-9 precursor, Rolex placed an encrypted call to his northern strike unit in Shimla ordering an immediate hit on Parthiban / Leo Das.',
  'What caller IMSI placed the directive call from the Ennore-North cell tower at 03:15 IST on March 14, 2024?',
  'Query the phone_records table for the caller_imsi connected to cell tower "Ennore-North" at 03:15.',
  'case_insensitive',
  '["404-45-89102482"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000004',
  'e0000000-0000-0000-0000-000000000001',
  4,
  'The Corrupt Deputy in Theog',
  'To track down Parthiban in Theog, Rolex routed a massive bribe via Scorpion Maritime Corp in Panama to a corrupt local deputy inspector in Shimla.',
  'What is the name of the recipient account holder who received a ₹50,00,000 wire transfer from Scorpion Maritime Corp?',
  'Inspect bank_transactions for a wire transfer of ₹50,00,000 sent by Scorpion Maritime Corp.',
  'case_insensitive',
  '["Sanjeev Kumar", "Sanjeev"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000005',
  'e0000000-0000-0000-0000-000000000001',
  5,
  'The Ambush at Nellore Yard',
  'On March 18, 2024, Anbu led a hit team to the Nellore Agricultural Checkpost to interrogate Dilli about the 2019 transit ledger. Dilli dismantled the squad and damaged their vehicle before contacting Vikram.',
  'What was the vehicle registration plate of the black Mahindra Scorpio used in the Nellore ambush?',
  'Look at vehicle_records for a black Scorpio sighted at the Nellore Highway on 2024-03-18.',
  'case_insensitive',
  '["AP-26-BK-9009"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000006',
  'e0000000-0000-0000-0000-000000000001',
  6,
  'The State Intelligence Mole',
  'When Leo Das, Dilli, Vikram, Amar, and Napoleon converged at the Ranipet Ceramic Factory, their coordinates were leaked to Rolex by a high-ranking mole in the State OCIU.',
  'Which corrupt intelligence officer leaked the Ranipet safehouse coordinates via message at 23:50 IST on 2024-04-04?',
  'Check the messages table for transmissions mentioning Ranipet on 2024-04-04, and cross-reference with access_logs or characters.',
  'case_insensitive',
  '["ACP Stephen Raj", "Stephen Raj", "K. Stephen Raj", "ACP K. Stephen Raj"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000007',
  'e0000000-0000-0000-0000-000000000001',
  7,
  'The Hawala Trail',
  'A massive hawala payment was wired through Dubai to reward Stephen Raj for delivering the Ranipet safehouse coordinates.',
  'What was the unique reference number of the ₹2,00,00,000 hawala payout transferred to account SR-77?',
  'Query bank_transactions for the ₹2,00,00,000 transfer to receiver account SR-77.',
  'case_insensitive',
  '["HWL-DXB-44102"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000008',
  'e0000000-0000-0000-0000-000000000001',
  8,
  'The Siege of Ranipet & Cartel Executions',
  'During the siege of the ceramic factory on April 5, 2024, Leo Das cornered Viper Selvam in the boiler room to extract the landing coordinates of the master synthesis lab.',
  'What was the exact forensic cause of death / lethal method used on Viper Selvam in the Ranipet boiler room?',
  'Query the autopsies or evidence table for the cause_of_death of Viper Selvam.',
  'case_insensitive',
  '["Manual Cervical Dislocation", "Neck Snap", "Manual Cervical Dislocation (Neck Snap)", "Cervical Dislocation"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000009',
  'e0000000-0000-0000-0000-000000000001',
  9,
  'The Floating Refinery at Royapuram',
  'Selvam confessed that Rolex was personally inspecting the narcotics synthesis conversion lab aboard a container ship berthed at Royapuram Coal Terminal Berth 11.',
  'What is the International Maritime Organization (IMO) vessel identification number of the ship MV Scorpia?',
  'Query the shipments table for the imo_number of the vessel MV Scorpia.',
  'case_insensitive',
  '["9182344"]'::jsonb,
  true
),
(
  'c0000000-0000-0000-0000-000000000010',
  'e0000000-0000-0000-0000-000000000001',
  10,
  'The Apex Execution & Final Deduction',
  'On April 6, 2024 at 03:18 IST, the final showdown occurred inside the MV Scorpia central laboratory hold. The supreme kingpin was eliminated, terminating the Das & Co drug legacy forever.',
  'Who killed Rolex, and what weapon was used? Format: <Killer> - <Weapon> (e.g. Leo Das - Kukri)',
  'Query the autopsies or kill_records table to identify the killer and weapon associated with victim Rolex.',
  'case_insensitive',
  '["Leo Das - Kukri", "Parthiban - Kukri", "Leo Das - Kukri blade", "Parthiban (Leo Das) - Kukri", "Leo Das - Hand-forged Kukri blade", "Parthiban - Hand-forged Kukri blade", "Leo Das", "Parthiban"]'::jsonb,
  true
);

-- 4. Level Hints
delete from public.level_hints where level_id in (select id from public.game_levels where event_id = 'e0000000-0000-0000-0000-000000000001');

insert into public.level_hints (level_id, title, body, penalty_minutes, sort_order)
values
('c0000000-0000-0000-0000-000000000001', 'Inspect Manifests', 'Run: SELECT container_number FROM shipments WHERE destination LIKE ''%Ennore%'' AND declared_manifest LIKE ''%Industrial%'';', 2, 1),
('c0000000-0000-0000-0000-000000000002', 'Target Gate 7', 'Run: SELECT card_or_badge_id, action_description FROM access_logs WHERE facility_location LIKE ''%Gate 7%'' AND access_timestamp::text LIKE ''2024-03-14%'';', 2, 1),
('c0000000-0000-0000-0000-000000000003', 'Tower Connection', 'Run: SELECT caller_imsi, notes FROM phone_records WHERE cell_tower = ''Ennore-North'';', 2, 1),
('c0000000-0000-0000-0000-000000000004', 'Panama Wire', 'Run: SELECT receiver_account, amount, reference_number FROM bank_transactions WHERE sender_account LIKE ''%Scorpion Maritime%'' AND amount = 5000000;', 2, 1),
('c0000000-0000-0000-0000-000000000005', 'Nellore Toll', 'Run: SELECT registration_number, vehicle_type, registered_owner FROM vehicle_records WHERE sighting_location LIKE ''%Nellore%'';', 2, 1),
('c0000000-0000-0000-0000-000000000006', 'Decrypted Message', 'Run: SELECT m.sender, m.message_text, p.caller_name FROM messages m JOIN phone_records p ON p.caller_imsi = m.sender WHERE m.message_text LIKE ''%Ranipet%'';', 2, 1),
('c0000000-0000-0000-0000-000000000007', 'Hawala Payout', 'Run: SELECT reference_number FROM bank_transactions WHERE receiver_account LIKE ''%SR-77%'' AND amount = 20000000;', 2, 1),
('c0000000-0000-0000-0000-000000000008', 'Autopsy Table', 'Run: SELECT victim_name, cause_of_death, killer_name FROM autopsies WHERE victim_name = ''Viper Selvam'';', 2, 1),
('c0000000-0000-0000-0000-000000000009', 'Vessel Registry', 'Run: SELECT imo_number FROM shipments WHERE vessel_name = ''MV Scorpia'';', 2, 1),
('c0000000-0000-0000-0000-000000000010', 'Final Confrontation', 'Run: SELECT killer_name, cause_of_death FROM autopsies WHERE victim_name = ''Rolex'';', 2, 1);

-- 5. Populate Investigation Data Tables

-- Clean and insert investigation.shipments
truncate table investigation.shipments cascade;
insert into investigation.shipments (
  shipment_id, container_number, vessel_name, imo_number, declared_manifest, actual_cargo, origin, destination, arrival_timestamp, clearance_status
) values
('SHP-401', 'MEDU-774910-2', null, null, 'Industrial Machinery Parts', '12 Cylinders Compound-9 Precursor', 'Theog Hub, Himachal Pradesh', 'Ennore Port CFS-4, Chennai', '2024-03-14 02:40:00+05:30', 'Cleared without physical inspection'),
('SHP-402', 'PAN-881290-0', 'MV Scorpia', '9182344', 'Refined Palm Oil & Industrial Solvents', 'Floating Narcotics Conversion Refinery', 'Port of Singapore', 'Royapuram Coal Berth 11, Chennai Port', '2024-04-05 18:00:00+05:30', 'Berthed at Royapuram Berth 11'),
('SHP-403', 'TGH-110022-9', 'SS Malabar', '9041288', 'Raw Agricultural Fertilizer', 'Unrefined Chemical Neutralizers', 'Kattupalli Port', 'Tuticorin Salt Yards', '2024-03-10 14:15:00+05:30', 'Standard Clearance'),
('SHP-404', 'BLR-992011-3', null, null, 'Electronic Spare Parts', 'Radio Transceivers & GPS Trackers', 'Bangalore Logistics Hub', 'Ranipet Warehouse', '2024-03-28 09:30:00+05:30', 'Inspected and Cleared');

-- Clean and insert investigation.locations
truncate table investigation.locations cascade;
insert into investigation.locations (
  location_id, name, state, latitude, longitude, description, significance
) values
('LOC-001', 'Ennore Port CFS-4', 'Tamil Nadu', 13.2312, 80.3211, 'Terminal Gate 7 container freight station in North Chennai.', 'Smuggling entry point for Compound-9 precursor.'),
('LOC-002', 'Parthiban Cafe & Residence', 'Himachal Pradesh', 31.1218, 77.3512, 'Quiet bakery and cafe in Theog, Shimla district.', 'Site of midnight hit squad attack and arson.'),
('LOC-003', 'Nellore Transport Yard', 'Andhra Pradesh', 14.4426, 79.9865, 'Heavy truck maintenance yard near AP-TN border.', 'Ambush site where Anbu confronted Dilli.'),
('LOC-004', 'Ranipet Ceramic Factory', 'Tamil Nadu', 12.9279, 79.3330, 'Abandoned industrial tile manufacturing facility.', 'Convergence point of Leo, Dilli, Vikram and siege battle.'),
('LOC-005', 'Royapuram Coal Berth 11', 'Tamil Nadu', 13.1147, 80.2981, 'Dock terminal at Chennai Port berthed with MV Scorpia.', 'Final showdown; death of Rolex and burning of refinery.'),
('LOC-006', 'Sandy Nullah Industrial Unit', 'Tamil Nadu', 11.4510, 76.6430, 'Former Das & Co. distillery and pharmaceutical factory in Nilgiris.', 'Original synthesis site of Compound-9 in 2004.');

-- Clean and insert investigation.access_logs
truncate table investigation.access_logs cascade;
insert into investigation.access_logs (
  log_id, card_or_badge_id, user_name, facility_location, access_timestamp, action_description
) values
('ACC-801', 'Card #4419', 'ACP Stephen Raj', 'State OCIU Evidence Vault', '2024-03-16 19:40:00+05:30', 'Retrieved sealed 2018 Das & Co case files and transit logs.'),
('ACC-802', 'ADMIN-01', 'Port Master Terminal', 'Ennore Port CFS-4 Gate 7', '2024-03-14 02:35:00+05:30', 'Gate 7 boom barrier bypassed for container truck TN-04-E-8819.'),
('ACC-803', 'Badge #9011', 'Chief Eng. MV Scorpia', 'MV Scorpia Hold 3', '2024-04-06 01:10:00+05:30', 'Access granted to Hold 3 / Central Chemical Conversion Lab.'),
('ACC-804', 'Card #1088', 'Constable Murugan', 'Vellore Central Prison Escort', '2024-03-12 04:15:00+05:30', 'Medical escort authorization signed for Adaikalam transfer.'),
('ACC-805', 'Badge #2204', 'Inspector Joshy', 'Theog Police Station Armory', '2024-03-21 17:00:00+05:30', 'Routine weapon inventory check; no ammunition missing.');

-- Clean and insert investigation.vehicle_records
truncate table investigation.vehicle_records cascade;
insert into investigation.vehicle_records (
  vehicle_id, registration_number, vehicle_type, registered_owner, sighting_location, sighting_timestamp
) values
('VEH-301', 'TN-04-E-8819', 'Ashok Leyland 16-Wheeler', 'Scorpion Maritime Logistics', 'Ennore Port CFS-4', '2024-03-14 02:40:00+05:30'),
('VEH-302', 'AP-26-BK-9009', 'Mahindra Scorpio (Black)', 'Anbu', 'Nellore Highway Toll Plaza', '2024-03-18 21:50:00+05:30'),
('VEH-303', 'HP-01-AA-4040', 'Mahindra Bolero Camper', 'Parthiban', 'Chandigarh-Shimla Highway', '2024-03-22 03:30:00+05:30'),
('VEH-304', 'TN-23-CC-1100', 'Tata 407 Armored Transport', 'Viper Selvam', 'Ranipet Industrial Gate', '2024-04-05 00:05:00+05:30'),
('VEH-305', 'TN-09-AX-5521', 'Toyota Fortuner (White)', 'ACP Stephen Raj', 'OCIU Chennai Headquarters', '2024-04-04 20:15:00+05:30');

-- Clean and insert investigation.phone_records
truncate table investigation.phone_records cascade;
insert into investigation.phone_records (
  call_id, caller_imsi, receiver_imsi, caller_name, receiver_name, call_timestamp, duration_seconds, cell_tower, notes
) values
('TEL-501', '404-45-89102482', '404-71-11928340', 'Rolex', 'Rover Unit-4 (Shimla)', '2024-03-14 03:15:00+05:30', 42, 'Ennore-North', 'Rolex orders hit on Leo Das in Theog to recover the cold ledger.'),
('TEL-502', '404-98-33019284', '404-11-00998822', 'Dilli', 'Agent Vikram', '2024-03-18 22:34:00+05:30', 115, 'Nellore-South', 'Dilli alerts Vikram after surviving Anbu ambush in Nellore.'),
('TEL-503', '404-22-77610293', '404-45-89102482', 'ACP Stephen Raj', 'Rolex', '2024-04-04 23:52:00+05:30', 28, 'Ranipet-Ind-2', 'Stephen Raj confirms target presence inside Ranipet Tile Works.'),
('TEL-504', '404-11-00998822', 'SAT-LINK-8830', 'Agent Vikram', 'Tactical Outpost', '2024-04-06 02:28:00+05:30', 15, 'Royapuram-Pier', 'Vikram coordinates Royapuram Port master electrical blackout.');

-- Clean and insert investigation.messages
truncate table investigation.messages cascade;
insert into investigation.messages (
  message_id, sender, receiver, sent_timestamp, message_text, encryption_type
) values
('MSG-01', '404-45-89102482', '404-88-29103940', '2024-03-15 08:20:00+05:30', 'Theog coordinates verified. Bring the Nilgiris ledger intact. Burn the rest.', 'AES-256'),
('MSG-02', '404-22-77610293', '404-45-89102482', '2024-04-04 23:50:00+05:30', 'Target is in Ranipet Tile Works. 5 men inside. Close the perimeter now.', 'Plaintext SMS'),
('MSG-03', 'SAT-LINK-01', 'FIELD-UNIT-AMAR', '2024-04-06 02:15:00+05:30', 'Blackout confirmed at 02:30. Weapons free on all perimeter targets.', 'Quantum Sat-Relay'),
('MSG-04', '404-71-11928340', '404-45-89102482', '2024-03-22 01:40:00+05:30', 'Cafe breached. Sanjeev down. Target is heading south.', 'AES-256');

-- Clean and insert investigation.bank_transactions
truncate table investigation.bank_transactions cascade;
insert into investigation.bank_transactions (
  transaction_id, sender_account, receiver_account, amount, transaction_type, reference_number, transaction_timestamp
) values
('TXN-901', 'Scorpion Maritime Corp (Panama)', 'Sanjeev Kumar (HDFC Shimla)', 5000000.00, 'Wire Transfer', 'SWIFT-SCORP-9910', '2024-03-16 11:30:00+05:30'),
('TXN-902', 'Hawala DXB Hub (Dubai)', 'SR-77 (Stephen Raj)', 20000000.00, 'Hawala Payout', 'HWL-DXB-44102', '2024-04-02 16:45:00+05:30'),
('TXN-903', 'Parthiban (SB-77192-01)', 'Cash Withdrawal (SBI Theog)', 2000000.00, 'Cash Withdrawal', 'ATM-THG-0021', '2024-03-22 06:15:00+05:30'),
('TXN-904', 'Das & Co Legacy Reserve', 'Scorpion Maritime Corp', 150000000.00, 'Automated Escrow', 'ESC-DAS-2004-99', '2024-03-14 02:00:00+05:30');

-- Clean and insert investigation.evidence
truncate table investigation.evidence cascade;
insert into investigation.evidence (
  evidence_id, item_name, recovered_location, recovery_timestamp, forensic_summary, matching_suspect
) values
('EVD-001', '32mm Drop-Forged Steel Wheel Spanner', 'Nellore Transport Yard', '2024-03-19 08:00:00+05:30', 'Heavy tool with epidermal tissue belonging to Anbu; bone fractures on cartel shooters.', 'Dilli'),
('EVD-002', '12 Spent 9x19mm Shell Casings (Hydra-Shok)', 'Theog Cafe, HP', '2024-03-22 09:30:00+05:30', 'Parabellum casings with firing pin impressions matching a customized Glock-19.', 'Parthiban (Leo Das)'),
('EVD-003', 'Autopsy: Crushed Hyoid Bone & Thoracic Trauma', 'Ranipet Ceramic Factory', '2024-04-05 06:00:00+05:30', 'Fatal tracheal collapse caused by blunt-force crowbar impact in kiln bay.', 'Dilli'),
('EVD-004', 'Damascus Steel Folding Blade', 'MV Scorpia Hold 3', '2024-04-06 06:00:00+05:30', 'Custom blade bearing Rolex fingerprint profile and apple fruit residue.', 'Rolex'),
('EVD-005', 'Sealed Encrypted Flash Drive', 'MV Scorpia Bridge Deck', '2024-04-06 06:15:00+05:30', 'Contains offshore banking routing, state police informant rosters, and wire logs.', 'ACP Stephen Raj'),
('EVD-006', 'Hand-Forged Curved Kukri Knife', 'MV Scorpia Central Hold', '2024-04-06 06:30:00+05:30', 'Heavy steel kukri blade matching fatal thoracic puncture wound on Rolex.', 'Parthiban (Leo Das)');

-- Clean and insert investigation.characters
truncate table investigation.characters cascade;
insert into investigation.characters (
  character_id, full_name, alias, primary_role, location_base, organization, status
) values
('CHAR-001', 'Parthiban / Leo Das', 'Leo Das', 'Cafe Owner & Former Das & Co Enforcer', 'Theog, Himachal Pradesh', 'Independent / Das & Co Legacy', 'Alive'),
('CHAR-002', 'Rolex', 'Rolex Sir', 'Supreme Syndicate Kingpin', 'Offshore / Chennai Port', 'Global Narcotics Syndicate', 'Deceased'),
('CHAR-003', 'Agent Vikram', 'Karnan / Commander', 'Leader of Aarambam Black-Ops', 'Shadow Safehouse Network', 'Aarambam Syndicate', 'Alive'),
('CHAR-004', 'Dilli', 'Dilli', 'Agricultural Truck Driver', 'Nellore, Andhra Pradesh', 'Independent / Kaithi Veteran', 'Alive'),
('CHAR-005', 'Amar', 'Amar', 'Black-Ops Field Operative', 'Bangalore / Chennai Hub', 'Aarambam Syndicate', 'Alive'),
('CHAR-006', 'Napoleon', 'Constable Napoleon', 'Communications & Safehouse Logistics', 'Trichy / Ranipet Safehouse', 'Aarambam Syndicate', 'Alive'),
('CHAR-007', 'Adaikalam', 'Adaikalam', 'Cartel Transit Lieutenant', 'Vellore / Ranipet', 'Rolex Syndicate', 'Deceased'),
('CHAR-008', 'Anbu', 'Anbu', 'Cartel Enforcer', 'Nellore / Chennai Port', 'Rolex Syndicate', 'Deceased'),
('CHAR-009', 'Viper Selvam', 'Selvam', 'Chemical Broker & Strike Commander', 'Chennai / Ranipet', 'Scorpion Maritime Logistics', 'Deceased'),
('CHAR-010', 'K. Stephen Raj', 'ACP Stephen Raj', 'Corrupt Senior Intelligence Officer', 'OCIU Headquarters Chennai', 'State Intelligence (Compromised)', 'Deceased'),
('CHAR-011', 'Sanjeev Kumar', 'Deputy Sanjeev', 'Rogue Deputy Inspector', 'Theog Police Station', 'Local Police (Compromised)', 'Deceased');

-- Clean and insert investigation.relationships
truncate table investigation.relationships cascade;
insert into investigation.relationships (
  relationship_id, person_a, person_b, relationship_type, details
) values
('REL-01', 'Antony Das', 'Leo Das', 'Father-Son', 'Antony Das created Compound-9; killed during Theog clash in 2023.'),
('REL-02', 'Harold Das', 'Rolex', 'Business Partners', 'Harold promised Rolex the northern precursor corridor in 2018 before fallout.'),
('REL-03', 'Adaikalam', 'Anbu', 'Brothers', 'Syndicate regional leaders operating under Rolex supervision.'),
('REL-04', 'Dilli', 'Amudha', 'Father-Daughter', 'Dilli fought through the 2019 siege to reunite with his daughter.'),
('REL-05', 'Agent Vikram', 'Amar', 'Commander-Operative', 'Core operatives of Aarambam tactical anti-cartel wing.');

-- Clean and insert investigation.timeline_events
truncate table investigation.timeline_events cascade;
insert into investigation.timeline_events (
  event_code, occurred_at, location_name, title, summary, key_individuals
) values
('EVT-101', '2024-03-14 02:40:00+05:30', 'Ennore Port CFS-4', 'Ghost Shipment Arrival', 'Truck TN-04-E-8819 clears customs with 12 cylinders of Compound-9.', 'Rolex, Viper Selvam, Stephen Raj'),
('EVT-102', '2024-03-18 22:15:00+05:30', 'Nellore Transport Yard', 'Ambush on Dilli', 'Anbu ambushes Dilli for the 2019 ledger; Dilli fights off hit team and calls Vikram.', 'Dilli, Anbu'),
('EVT-103', '2024-03-22 01:10:00+05:30', 'Theog Cafe, HP', 'Attack on Parthiban Cafe', '12-man cartel hit squad breaches cafe; Parthiban eliminates squad and interrogates Sanjeev.', 'Parthiban, Sanjeev'),
('EVT-104', '2024-04-04 23:45:00+05:30', 'Ranipet Ceramic Factory', 'Convergence & Safehouse Leak', 'Leo, Dilli, Vikram, Amar, and Napoleon unite; Stephen Raj leaks GPS to cartel.', 'Vikram, Leo, Dilli, Stephen Raj'),
('EVT-105', '2024-04-05 00:38:00+05:30', 'Ranipet Ceramic Factory', 'Adaikalam Executed', 'Dilli corners Adaikalam in Kiln 3 and crushes his windpipe with steel crowbar.', 'Dilli, Adaikalam'),
('EVT-106', '2024-04-05 00:44:00+05:30', 'Ranipet Boiler Room', 'Viper Selvam Executed', 'Leo Das interrogates Viper Selvam, discovers MV Scorpia coordinates, and snaps his neck.', 'Leo Das, Viper Selvam'),
('EVT-107', '2024-04-06 02:58:00+05:30', 'MV Scorpia Bridge Deck', 'ACP Stephen Raj Executed', 'Amar shoots Stephen Raj center-mass and secures encrypted flash drive.', 'Amar, Stephen Raj'),
('EVT-108', '2024-04-06 03:05:00+05:30', 'MV Scorpia Ballast Corridor', 'Anbu Executed', 'Dilli strangles Anbu with heavy mooring chain in ballast corridor.', 'Dilli, Anbu'),
('EVT-109', '2024-04-06 03:18:00+05:30', 'MV Scorpia Central Hold', 'Rolex Executed', 'Leo Das battles Rolex and drives a kukri knife through his chest.', 'Leo Das, Rolex');

-- Clean and insert investigation.red_herrings
truncate table investigation.red_herrings cascade;
insert into investigation.red_herrings (
  record_id, lead_code, apparent_theory, forensic_truth, debunking_evidence
) values
('RED-01', 'RED-SHIMLA-LEAK', 'Initial intelligence suggested Inspector Joshy sold out Parthiban to the cartel.', 'Inspector Joshy was innocent; his junior Sanjeev stole case files after ₹50,00,000 wire from Panama.', 'Bank transaction TXN-901 confirmed payout directly to Sanjeev Kumar.'),
('RED-02', 'RED-NELLORE-DURAI', 'OCIU intelligence files claimed Dilli was a kingpin operating under alias Nellore Durai.', 'Fabricated paperwork forged by Stephen Raj to justify a staged police encounter.', 'Sealed flash drive EVD-005 found on Stephen Raj contained fake template dossiers.'),
('RED-03', 'RED-SANDY-NULLAH', 'Old news reports from 2004 claimed all Compound-9 stocks were destroyed in a factory fire.', 'Harold Das secretly relocated 500L to a dormant automated cold storage unit in Theog.', 'Automated shipment SHP-401 dispatched Compound-9 from Theog 20 years later.');

-- Clean and insert investigation.autopsies
truncate table investigation.autopsies cascade;
insert into investigation.autopsies (
  autopsy_id, victim_name, time_of_death, location_found, cause_of_death, killer_name, motive
) values
('AUT-01', 'Sanjeev Kumar', '2024-03-22 01:25:00+05:30', 'Theog Cafe Hearth, HP', 'Single 9mm gunshot to head', 'Parthiban (Leo Das)', 'Betrayal / Leaking family location to cartel'),
('AUT-02', 'Adaikalam', '2024-04-05 00:38:00+05:30', 'Ranipet Factory Kiln 3, TN', '32mm steel crowbar / Tracheal crush', 'Dilli', 'Self-defense / Protecting daughter Amudha'),
('AUT-03', 'Viper Selvam', '2024-04-05 00:44:00+05:30', 'Ranipet Boiler Room, TN', 'Manual Cervical Dislocation (Neck Snap)', 'Parthiban (Leo Das)', 'Interrogation / Eradicating Rolex strike commander'),
('AUT-04', 'ACP K. Stephen Raj', '2024-04-06 02:58:00+05:30', 'MV Scorpia Bridge Deck', 'Two 9x19mm rounds to chest (SIG Sauer MCX)', 'Amar', 'Eliminating cartel mole inside State Intelligence'),
('AUT-05', 'Anbu', '2024-04-06 03:05:00+05:30', 'MV Scorpia Ballast Corridor', 'Heavy industrial mooring chain strangulation', 'Dilli', 'Self-defense / Avenging harassment of family'),
('AUT-06', 'Rolex', '2024-04-06 03:18:00+05:30', 'MV Scorpia Central Hold', 'Hand-forged Kukri blade through thoracic cavity', 'Parthiban (Leo Das)', 'Protecting family / Terminating Das & Co drug legacy');

-- Clean and insert investigation.kill_records
truncate table investigation.kill_records cascade;
insert into investigation.kill_records (
  record_id, victim, killer, weapon, date_time, location, plot_impact
) values
('KIL-01', 'Sanjeev Kumar', 'Parthiban (Leo Das)', 'Glock-19 (9x19mm)', '2024-03-22 01:25:00+05:30', 'Theog Cafe, HP', 'Eliminates Rolex intelligence arm in Himachal.'),
('KIL-02', 'Adaikalam', 'Dilli', '32mm Steel Crowbar', '2024-04-05 00:38:00+05:30', 'Ranipet Factory Kiln 3, TN', 'Closes the Kaithi syndicate chapter forever.'),
('KIL-03', 'Viper Selvam', 'Parthiban (Leo Das)', 'Manual Cervical Dislocation', '2024-04-05 00:44:00+05:30', 'Ranipet Boiler Room, TN', 'Reveals location of MV Scorpia and the port lab.'),
('KIL-04', 'ACP K. Stephen Raj', 'Amar', 'SIG Sauer MCX (9mm)', '2024-04-06 02:58:00+05:30', 'MV Scorpia Bridge Deck', 'Yields encrypted flash drive with offshore accounts.'),
('KIL-05', 'Anbu', 'Dilli', 'Mooring Chain', '2024-04-06 03:05:00+05:30', 'MV Scorpia Ballast Corridor', 'Completely wipes out Adaikalam bloodline.'),
('KIL-06', 'Rolex', 'Leo Das', 'Hand-forged Kukri Blade', '2024-04-06 03:18:00+05:30', 'MV Scorpia Central Hold', 'Destroys apex leadership of South Asian cartel.');

-- 6. Preliminary DBMS/SQL Quiz Questions & Options
delete from public.quiz_questions where event_id = 'e0000000-0000-0000-0000-000000000001';

insert into public.quiz_questions (id, event_id, prompt, points, sort_order)
values
('d0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', 'Which SQL clause is used to filter rows based on a specified search condition?', 1, 1),
('d0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000001', 'Which type of JOIN returns all records from the left table and matched records from the right table?', 1, 2),
('d0000000-0000-0000-0000-000000000003', 'e0000000-0000-0000-0000-000000000001', 'Which aggregate function returns the total count of non-null rows in a column?', 1, 3),
('d0000000-0000-0000-0000-000000000004', 'e0000000-0000-0000-0000-000000000001', 'Which clause must be used to filter groups created by a GROUP BY clause?', 1, 4),
('d0000000-0000-0000-0000-000000000005', 'e0000000-0000-0000-0000-000000000001', 'Which SQL operator tests whether a value falls within an inclusive specified range?', 1, 5);

insert into public.quiz_options (question_id, option_text, is_correct)
values
('d0000000-0000-0000-0000-000000000001', 'WHERE', true),
('d0000000-0000-0000-0000-000000000001', 'ORDER BY', false),
('d0000000-0000-0000-0000-000000000001', 'GROUP BY', false),
('d0000000-0000-0000-0000-000000000001', 'SELECT', false),

('d0000000-0000-0000-0000-000000000002', 'LEFT JOIN', true),
('d0000000-0000-0000-0000-000000000002', 'INNER JOIN', false),
('d0000000-0000-0000-0000-000000000002', 'RIGHT JOIN', false),
('d0000000-0000-0000-0000-000000000002', 'CROSS JOIN', false),

('d0000000-0000-0000-0000-000000000003', 'COUNT()', true),
('d0000000-0000-0000-0000-000000000003', 'SUM()', false),
('d0000000-0000-0000-0000-000000000003', 'TOTAL()', false),
('d0000000-0000-0000-0000-000000000003', 'AVG()', false),

('d0000000-0000-0000-0000-000000000004', 'HAVING', true),
('d0000000-0000-0000-0000-000000000004', 'WHERE', false),
('d0000000-0000-0000-0000-000000000004', 'ORDER BY', false),
('d0000000-0000-0000-0000-000000000004', 'FILTER', false),

('d0000000-0000-0000-0000-000000000005', 'BETWEEN', true),
('d0000000-0000-0000-0000-000000000005', 'IN', false),
('d0000000-0000-0000-0000-000000000005', 'LIKE', false),
('d0000000-0000-0000-0000-000000000005', 'EXISTS', false);
