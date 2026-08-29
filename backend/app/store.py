from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import Any
from uuid import uuid4

import asyncpg

from .config import get_settings
from .models import (
    AnswerSubmission,
    Event,
    EventConfig,
    Hint,
    InvestigationTable,
    Level,
    Participant,
    QueryLog,
    QuizOption,
    QuizQuestion,
    Session,
    Story,
    TableColumn,
    now_utc,
)

logger = logging.getLogger(__name__)


class GameError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "game_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    duration_ms: int


def _serialize_cell(val: Any) -> Any:
    if isinstance(val, (datetime,)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val


class GameStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.event = Event()
        self.levels: list[Level] = []
        self.tables: list[InvestigationTable] = []
        self.hints: list[Hint] = []
        self.quiz_questions: list[QuizQuestion] = []
        self.participants: dict[str, Participant] = {}
        self.sessions: dict[str, Session] = {}
        self.query_logs: list[QueryLog] = []
        self.answer_submissions: list[AnswerSubmission] = []
        self._lock = asyncio.Lock()
        self._db_pool: asyncpg.Pool | None = None

        # In-memory datasets for local/fallback execution
        self._local_data: dict[str, list[dict[str, Any]]] = {}

        # Initialize with complete LCU: ECLIPSE story and investigation tables
        self._load_lcu_eclipse_case()

    async def get_db_pool(self) -> asyncpg.Pool | None:
        if not self.settings.supabase_database_url:
            return None
        if self._db_pool is None:
            try:
                # Asyncpg connection to Supabase pooler
                url = self.settings.supabase_database_url
                self._db_pool = await asyncpg.create_pool(
                    dsn=url,
                    min_size=1,
                    max_size=10,
                    command_timeout=self.settings.query_timeout_ms / 1000.0,
                    statement_cache_size=0,  # Required for PgBouncer transaction / session mode
                )
                logger.info("Successfully connected to Supabase PostgreSQL pool.")
            except Exception as exc:
                logger.warning(f"Could not connect to Supabase PostgreSQL pool: {exc}. Falling back to in-memory engine.")
                self._db_pool = None
        return self._db_pool

    def _load_lcu_eclipse_case(self) -> None:
        """Seed the complete LCU: ECLIPSE event, levels, clues, hints, tables, and records."""
        self.event = Event(
            id="e0000000-0000-0000-0000-000000000001",
            slug="invente-2026",
            name="MURDER MYSTIQL: LCU ECLIPSE",
            tagline="Invente 2026 SQL Investigation Challenge",
            description="A high-stakes relational SQL mystery set in the aftermath of the Das & Co collapse.",
            status="live",
            config=EventConfig(
                wrong_answer_penalty_minutes=5,
                wrong_answer_lock_seconds=60,
                hint_penalty_default_minutes=2,
                allow_pause=False,
                max_query_rows=200,
                query_timeout_ms=3000,
                quiz_required=False,
                quiz_qualify_score=3,
            ),
            story=Story(
                title="LCU: ECLIPSE",
                prologue=(
                    "The foundation of the South Indian narcotics corridor rests on three cataclysms: "
                    "Trichy (2019), Chennai (2022), and Theog (2023). When an automated 20-year maintenance timer "
                    "in Theog triggers a backdated shipment of Compound-9 to Ennore Port under Scorpion Maritime, "
                    "Rolex discovers that Leo Das is alive and living as Parthiban. A lethal war converges across "
                    "Nellore, Ranipet, and Royapuram Port."
                ),
                description="Investigate the ghost shipments, security bypasses, and final confrontation through SQL queries.",
                disclaimer="LCU: ECLIPSE is fan-made fiction created for entertainment and mystery-game purposes. It is not official canon of the Lokesh Cinematic Universe.",
            ),
        )

        # 10 Investigation Levels
        self.levels = [
            Level(
                id="l0000000-0000-0000-0000-000000000001",
                event_id=self.event.id,
                level_number=1,
                title="The Ghost Shipment at Ennore",
                narrative_context=(
                    "On March 14, 2024 at 02:40 IST, a dark green Ashok Leyland truck (TN-04-E-8819) cleared "
                    "customs at Ennore Port CFS-4 without physical inspection. The cargo manifest listed industrial "
                    "machinery parts consigned to Scorpion Maritime Logistics, but secretly contained 12 pressurized "
                    "cylinders of Compound-9 chemical precursor."
                ),
                objective="What is the container tracking number of the suspicious shipment that arrived at Ennore Port CFS-4?",
                clue="Query the shipments table for shipments arriving at Ennore Port with a declared manifest of Industrial Machinery.",
                answer_type="case_insensitive",
                answer_values=["MEDU-774910-2"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000002",
                event_id=self.event.id,
                level_number=2,
                title="The Security Breach & Customs Bypass",
                narrative_context=(
                    "Rolex and his compromised associates oversaw the arrival of the Compound-9 precursor. Security logs "
                    "show that Terminal Gate 7 boom barrier was deliberately bypassed just minutes before truck TN-04-E-8819 cleared."
                ),
                objective="What biometric override ID or badge was used to bypass the Gate 7 boom barrier at Ennore Port CFS-4?",
                clue="Check the access_logs table for security override events at Gate 7 on 2024-03-14 around 02:35 IST.",
                answer_type="case_insensitive",
                answer_values=["ADMIN-01"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000003",
                event_id=self.event.id,
                level_number=3,
                title="Intercepting the Command Call",
                narrative_context=(
                    "Upon receiving confirmation of the Compound-9 arrival, Rolex transmitted a directive call to his northern "
                    "strike unit in Shimla ordering an immediate hit on Parthiban / Leo Das."
                ),
                objective="What caller IMSI placed the directive call from the Ennore-North cell tower at 03:15 IST on March 14, 2024?",
                clue="Query phone_records for calls originating from the 'Ennore-North' cell tower at 03:15 on 2024-03-14.",
                answer_type="case_insensitive",
                answer_values=["404-45-89102482"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000004",
                event_id=self.event.id,
                level_number=4,
                title="The Corrupt Deputy in Theog",
                narrative_context=(
                    "To coordinate the hit squad in Himachal, Rolex routed a bribe from Scorpion Maritime Corp in Panama "
                    "to a corrupt local police officer in Shimla."
                ),
                objective="What is the recipient account name of the rogue police officer who received a ₹50,00,000 wire transfer?",
                clue="Inspect bank_transactions for a ₹50,00,000 wire transfer sent by Scorpion Maritime Corp.",
                answer_type="case_insensitive",
                answer_values=["Sanjeev Kumar", "Sanjeev"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000005",
                event_id=self.event.id,
                level_number=5,
                title="The Ambush at Nellore Yard",
                narrative_context=(
                    "On March 18, 2024, Anbu led a hit team to the Nellore Agricultural Checkpost to interrogate Dilli about "
                    "the 2019 hidden transit lockbox. Dilli fought off the attackers, who fled in a black Mahindra Scorpio."
                ),
                objective="What was the vehicle registration plate of the black Mahindra Scorpio used in the Nellore ambush?",
                clue="Query vehicle_records for a black Mahindra Scorpio sighted near the Nellore Highway on 2024-03-18.",
                answer_type="case_insensitive",
                answer_values=["AP-26-BK-9009"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000006",
                event_id=self.event.id,
                level_number=6,
                title="The State Intelligence Mole",
                narrative_context=(
                    "When Leo Das, Dilli, Vikram, Amar, and Napoleon converged at the Ranipet Ceramic Factory, their location "
                    "was leaked to Rolex by a high-ranking mole in the State OCIU."
                ),
                objective="Which corrupt intelligence officer leaked the Ranipet safehouse coordinates via message at 23:50 IST on 2024-04-04?",
                clue="Check messages mentioning Ranipet sent on 2024-04-04, and cross-reference the sender with access_logs.",
                answer_type="case_insensitive",
                answer_values=["ACP Stephen Raj", "Stephen Raj", "K. Stephen Raj", "ACP K. Stephen Raj"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000007",
                event_id=self.event.id,
                level_number=7,
                title="The Hawala Trail",
                narrative_context=(
                    "A massive hawala payoff was wired via Dubai to reward Stephen Raj for delivering the Ranipet safehouse coordinates."
                ),
                objective="What was the reference number of the ₹2,00,00,000 hawala payout transferred to account SR-77?",
                clue="Query bank_transactions for the ₹2,00,00,000 transaction routed to receiver account SR-77.",
                answer_type="case_insensitive",
                answer_values=["HWL-DXB-44102"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000008",
                event_id=self.event.id,
                level_number=8,
                title="The Siege of Ranipet & Cartel Executions",
                narrative_context=(
                    "During the siege of the Ranipet factory, Leo Das cornered Viper Selvam in the boiler room to discover "
                    "where Rolex was assembling the master narcotics synthesis refinery."
                ),
                objective="What was the forensic cause of death / lethal method used to execute Viper Selvam in the Ranipet boiler room?",
                clue="Query the autopsies or evidence table for the cause_of_death of Viper Selvam.",
                answer_type="case_insensitive",
                answer_values=[
                    "Manual Cervical Dislocation",
                    "Neck Snap",
                    "Manual Cervical Dislocation (Neck Snap)",
                    "Cervical Dislocation",
                ],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000009",
                event_id=self.event.id,
                level_number=9,
                title="The Floating Refinery at Royapuram",
                narrative_context=(
                    "Selvam confessed that Rolex was personally inspecting the narcotics conversion refinery aboard a cargo vessel "
                    "berthed at Royapuram Coal Berth 11 under a Panamanian flag."
                ),
                objective="What is the International Maritime Organization (IMO) vessel identification number of MV Scorpia?",
                clue="Query shipments for the imo_number of the cargo vessel MV Scorpia.",
                answer_type="case_insensitive",
                answer_values=["9182344"],
                active=True,
            ),
            Level(
                id="l0000000-0000-0000-0000-000000000010",
                event_id=self.event.id,
                level_number=10,
                title="The Apex Execution & Final Deduction",
                narrative_context=(
                    "On April 6, 2024 at 03:18 IST, the final confrontation occurred inside the MV Scorpia central hold. "
                    "The supreme kingpin was eliminated, destroying the Das & Co drug legacy forever."
                ),
                objective="Who killed Rolex, and what weapon was used? Format: <Killer> - <Weapon> (e.g. Leo Das - Kukri)",
                clue="Query the autopsies or kill_records table to identify the killer and weapon associated with victim Rolex.",
                answer_type="case_insensitive",
                answer_values=[
                    "Leo Das - Kukri",
                    "Parthiban - Kukri",
                    "Leo Das - Kukri blade",
                    "Parthiban (Leo Das) - Kukri",
                    "Leo Das - Hand-forged Kukri blade",
                    "Parthiban - Hand-forged Kukri blade",
                    "Leo Das",
                    "Parthiban",
                ],
                active=True,
            ),
        ]

        # Table catalog with unlock levels
        self.tables = [
            InvestigationTable(
                name="shipments",
                label="Port Cargo Shipments",
                unlock_level=1,
                description="Customs manifests, vessels, IMO numbers, origins, and declared vs actual cargo.",
                columns=[
                    TableColumn("shipment_id", "text", False, True),
                    TableColumn("container_number", "text", False),
                    TableColumn("vessel_name", "text"),
                    TableColumn("imo_number", "text"),
                    TableColumn("declared_manifest", "text", False),
                    TableColumn("actual_cargo", "text", False),
                    TableColumn("origin", "text", False),
                    TableColumn("destination", "text", False),
                    TableColumn("arrival_timestamp", "timestamptz", False),
                    TableColumn("clearance_status", "text", False),
                ],
            ),
            InvestigationTable(
                name="locations",
                label="Geographic Locations",
                unlock_level=1,
                description="Key operational hubs, coordinates, and tactical facilities.",
                columns=[
                    TableColumn("location_id", "text", False, True),
                    TableColumn("name", "text", False),
                    TableColumn("state", "text", False),
                    TableColumn("latitude", "numeric(9,4)"),
                    TableColumn("longitude", "numeric(9,4)"),
                    TableColumn("description", "text"),
                    TableColumn("significance", "text", False),
                ],
            ),
            InvestigationTable(
                name="access_logs",
                label="Facility Security Access Logs",
                unlock_level=2,
                description="Biometric overrides, badge swipes, and terminal security access events.",
                columns=[
                    TableColumn("log_id", "text", False, True),
                    TableColumn("card_or_badge_id", "text", False),
                    TableColumn("user_name", "text", False),
                    TableColumn("facility_location", "text", False),
                    TableColumn("access_timestamp", "timestamptz", False),
                    TableColumn("action_description", "text", False),
                ],
            ),
            InvestigationTable(
                name="vehicle_records",
                label="Vehicle Sightings & Registration",
                unlock_level=2,
                description="Highway toll sightings, truck plates, and registered owner records.",
                columns=[
                    TableColumn("vehicle_id", "text", False, True),
                    TableColumn("registration_number", "text", False),
                    TableColumn("vehicle_type", "text", False),
                    TableColumn("registered_owner", "text", False),
                    TableColumn("sighting_location", "text", False),
                    TableColumn("sighting_timestamp", "timestamptz", False),
                ],
            ),
            InvestigationTable(
                name="phone_records",
                label="Cellular Intercepts & Call Logs",
                unlock_level=3,
                description="IMSI intercepts, cell tower connections, durations, and call notes.",
                columns=[
                    TableColumn("call_id", "text", False, True),
                    TableColumn("caller_imsi", "text", False),
                    TableColumn("receiver_imsi", "text", False),
                    TableColumn("caller_name", "text"),
                    TableColumn("receiver_name", "text"),
                    TableColumn("call_timestamp", "timestamptz", False),
                    TableColumn("duration_seconds", "integer", False),
                    TableColumn("cell_tower", "text", False),
                    TableColumn("notes", "text"),
                ],
            ),
            InvestigationTable(
                name="bank_transactions",
                label="Financial & Hawala Transactions",
                unlock_level=4,
                description="Offshore wire transfers, hawala payouts, and cash withdrawals.",
                columns=[
                    TableColumn("transaction_id", "text", False, True),
                    TableColumn("sender_account", "text", False),
                    TableColumn("receiver_account", "text", False),
                    TableColumn("amount", "numeric(14,2)", False),
                    TableColumn("transaction_type", "text", False),
                    TableColumn("reference_number", "text", False, True),
                    TableColumn("transaction_timestamp", "timestamptz", False),
                ],
            ),
            InvestigationTable(
                name="messages",
                label="Decrypted Radio & SMS Transmissions",
                unlock_level=4,
                description="Field transmissions, coordinate leaks, and directive messages.",
                columns=[
                    TableColumn("message_id", "text", False, True),
                    TableColumn("sender", "text", False),
                    TableColumn("receiver", "text", False),
                    TableColumn("sent_timestamp", "timestamptz", False),
                    TableColumn("message_text", "text", False),
                    TableColumn("encryption_type", "text", False),
                ],
            ),
            InvestigationTable(
                name="evidence",
                label="Forensics & Physical Ballistics",
                unlock_level=5,
                description="Weapons, spent casings, tools, and digital flash drives recovered.",
                columns=[
                    TableColumn("evidence_id", "text", False, True),
                    TableColumn("item_name", "text", False),
                    TableColumn("recovered_location", "text", False),
                    TableColumn("recovery_timestamp", "timestamptz", False),
                    TableColumn("forensic_summary", "text", False),
                    TableColumn("matching_suspect", "text"),
                ],
            ),
            InvestigationTable(
                name="characters",
                label="Dossier of Suspects & Operatives",
                unlock_level=6,
                description="Operative aliases, affiliations, roles, and status.",
                columns=[
                    TableColumn("character_id", "text", False, True),
                    TableColumn("full_name", "text", False),
                    TableColumn("alias", "text"),
                    TableColumn("primary_role", "text", False),
                    TableColumn("location_base", "text", False),
                    TableColumn("organization", "text", False),
                    TableColumn("status", "text", False),
                ],
            ),
            InvestigationTable(
                name="relationships",
                label="Syndicate Ties & Kinship Matrix",
                unlock_level=6,
                description="Connections between syndicate leaders, family ties, and alliances.",
                columns=[
                    TableColumn("relationship_id", "text", False, True),
                    TableColumn("person_a", "text", False),
                    TableColumn("person_b", "text", False),
                    TableColumn("relationship_type", "text", False),
                    TableColumn("details", "text", False),
                ],
            ),
            InvestigationTable(
                name="timeline_events",
                label="Master Incident Timeline",
                unlock_level=7,
                description="Chronological timeline of incidents from 2004 through Royapuram 2024.",
                columns=[
                    TableColumn("event_code", "text", False, True),
                    TableColumn("occurred_at", "timestamptz", False),
                    TableColumn("location_name", "text", False),
                    TableColumn("title", "text", False),
                    TableColumn("summary", "text", False),
                    TableColumn("key_individuals", "text", False),
                ],
            ),
            InvestigationTable(
                name="red_herrings",
                label="False Leads & Forged Intel Dossiers",
                unlock_level=8,
                description="Fabricated OCIU records, false leaks, and debunking evidence.",
                columns=[
                    TableColumn("record_id", "text", False, True),
                    TableColumn("lead_code", "text", False),
                    TableColumn("apparent_theory", "text", False),
                    TableColumn("forensic_truth", "text", False),
                    TableColumn("debunking_evidence", "text", False),
                ],
            ),
            InvestigationTable(
                name="autopsies",
                label="Coroner Post-Mortem Reports",
                unlock_level=8,
                description="Post-mortem findings, causes of death, time of death, and motives.",
                columns=[
                    TableColumn("autopsy_id", "text", False, True),
                    TableColumn("victim_name", "text", False),
                    TableColumn("time_of_death", "timestamptz", False),
                    TableColumn("location_found", "text", False),
                    TableColumn("cause_of_death", "text", False),
                    TableColumn("killer_name", "text", False),
                    TableColumn("motive", "text", False),
                ],
            ),
            InvestigationTable(
                name="kill_records",
                label="Final Fatal Confrontation Log",
                unlock_level=9,
                description="Who killed whom, lethal methods, exact locations, and plot impacts.",
                columns=[
                    TableColumn("record_id", "text", False, True),
                    TableColumn("victim", "text", False),
                    TableColumn("killer", "text", False),
                    TableColumn("weapon", "text", False),
                    TableColumn("date_time", "timestamptz", False),
                    TableColumn("location", "text", False),
                    TableColumn("plot_impact", "text", False),
                ],
            ),
        ]

        # Hints
        self.hints = [
            Hint("h01", "l0000000-0000-0000-0000-000000000001", "Inspect Manifests", "Run: SELECT container_number FROM shipments WHERE destination LIKE '%Ennore%' AND declared_manifest LIKE '%Industrial%';", 2),
            Hint("h02", "l0000000-0000-0000-0000-000000000002", "Target Gate 7", "Run: SELECT card_or_badge_id, action_description FROM access_logs WHERE facility_location LIKE '%Gate 7%' AND access_timestamp::text LIKE '2024-03-14%';", 2),
            Hint("h03", "l0000000-0000-0000-0000-000000000003", "Tower Connection", "Run: SELECT caller_imsi, notes FROM phone_records WHERE cell_tower = 'Ennore-North' AND call_timestamp::text LIKE '2024-03-14 03:15%';", 2),
            Hint("h04", "l0000000-0000-0000-0000-000000000004", "Panama Wire", "Run: SELECT receiver_account, amount, reference_number FROM bank_transactions WHERE sender_account LIKE '%Scorpion Maritime%' AND amount = 5000000;", 2),
            Hint("h05", "l0000000-0000-0000-0000-000000000005", "Nellore Toll", "Run: SELECT registration_number, vehicle_type, registered_owner FROM vehicle_records WHERE sighting_location LIKE '%Nellore%';", 2),
            Hint("h06", "l0000000-0000-0000-0000-000000000006", "Decrypted Message", "Run: SELECT m.sender, m.message_text, p.caller_name FROM messages m JOIN phone_records p ON p.caller_imsi = m.sender WHERE m.message_text LIKE '%Ranipet%';", 2),
            Hint("h07", "l0000000-0000-0000-0000-000000000007", "Hawala Payout", "Run: SELECT reference_number FROM bank_transactions WHERE receiver_account LIKE '%SR-77%' AND amount = 20000000;", 2),
            Hint("h08", "l0000000-0000-0000-0000-000000000008", "Autopsy Table", "Run: SELECT victim_name, cause_of_death, killer_name FROM autopsies WHERE victim_name = 'Viper Selvam';", 2),
            Hint("h09", "l0000000-0000-0000-0000-000000000009", "Vessel Registry", "Run: SELECT imo_number FROM shipments WHERE vessel_name = 'MV Scorpia';", 2),
            Hint("h10", "l0000000-0000-0000-0000-000000000010", "Final Confrontation", "Run: SELECT killer_name, cause_of_death FROM autopsies WHERE victim_name = 'Rolex';", 2),
        ]

        # Quiz Questions for Preliminary Qualification
        self.quiz_questions = [
            QuizQuestion(
                id="q1",
                prompt="Which SQL clause is used to filter rows based on a specified search condition?",
                points=1,
                options=[
                    QuizOption("q1_1", "WHERE", True),
                    QuizOption("q1_2", "ORDER BY", False),
                    QuizOption("q1_3", "GROUP BY", False),
                    QuizOption("q1_4", "SELECT", False),
                ],
            ),
            QuizQuestion(
                id="q2",
                prompt="Which type of JOIN returns all records from the left table and matched records from the right table?",
                points=1,
                options=[
                    QuizOption("q2_1", "LEFT JOIN", True),
                    QuizOption("q2_2", "INNER JOIN", False),
                    QuizOption("q2_3", "RIGHT JOIN", False),
                    QuizOption("q2_4", "CROSS JOIN", False),
                ],
            ),
            QuizQuestion(
                id="q3",
                prompt="Which aggregate function returns the total count of rows in a table?",
                points=1,
                options=[
                    QuizOption("q3_1", "COUNT()", True),
                    QuizOption("q3_2", "SUM()", False),
                    QuizOption("q3_3", "TOTAL()", False),
                    QuizOption("q3_4", "AVG()", False),
                ],
            ),
            QuizQuestion(
                id="q4",
                prompt="Which clause must be used to filter groups created by a GROUP BY clause?",
                points=1,
                options=[
                    QuizOption("q4_1", "HAVING", True),
                    QuizOption("q4_2", "WHERE", False),
                    QuizOption("q4_3", "ORDER BY", False),
                    QuizOption("q4_4", "FILTER", False),
                ],
            ),
            QuizQuestion(
                id="q5",
                prompt="Which SQL operator tests whether a value falls within an inclusive specified range?",
                points=1,
                options=[
                    QuizOption("q5_1", "BETWEEN", True),
                    QuizOption("q5_2", "IN", False),
                    QuizOption("q5_3", "LIKE", False),
                    QuizOption("q5_4", "EXISTS", False),
                ],
            ),
        ]

        # Seed in-memory tables for local / fallback mode
        self._local_data = {
            "shipments": [
                {
                    "shipment_id": "SHP-401",
                    "container_number": "MEDU-774910-2",
                    "vessel_name": None,
                    "imo_number": None,
                    "declared_manifest": "Industrial Machinery Parts",
                    "actual_cargo": "12 Cylinders Compound-9 Precursor",
                    "origin": "Theog Hub, Himachal Pradesh",
                    "destination": "Ennore Port CFS-4, Chennai",
                    "arrival_timestamp": "2024-03-14 02:40:00+05:30",
                    "clearance_status": "Cleared without physical inspection",
                },
                {
                    "shipment_id": "SHP-402",
                    "container_number": "PAN-881290-0",
                    "vessel_name": "MV Scorpia",
                    "imo_number": "9182344",
                    "declared_manifest": "Refined Palm Oil & Industrial Solvents",
                    "actual_cargo": "Floating Narcotics Conversion Refinery",
                    "origin": "Port of Singapore",
                    "destination": "Royapuram Coal Berth 11, Chennai Port",
                    "arrival_timestamp": "2024-04-05 18:00:00+05:30",
                    "clearance_status": "Berthed at Royapuram Berth 11",
                },
                {
                    "shipment_id": "SHP-403",
                    "container_number": "TGH-110022-9",
                    "vessel_name": "SS Malabar",
                    "imo_number": "9041288",
                    "declared_manifest": "Raw Agricultural Fertilizer",
                    "actual_cargo": "Unrefined Chemical Neutralizers",
                    "origin": "Kattupalli Port",
                    "destination": "Tuticorin Salt Yards",
                    "arrival_timestamp": "2024-03-10 14:15:00+05:30",
                    "clearance_status": "Standard Clearance",
                },
                {
                    "shipment_id": "SHP-404",
                    "container_number": "BLR-992011-3",
                    "vessel_name": None,
                    "imo_number": None,
                    "declared_manifest": "Electronic Spare Parts",
                    "actual_cargo": "Radio Transceivers & GPS Trackers",
                    "origin": "Bangalore Logistics Hub",
                    "destination": "Ranipet Warehouse",
                    "arrival_timestamp": "2024-03-28 09:30:00+05:30",
                    "clearance_status": "Inspected and Cleared",
                },
            ],
            "locations": [
                {
                    "location_id": "LOC-001",
                    "name": "Ennore Port CFS-4",
                    "state": "Tamil Nadu",
                    "latitude": 13.2312,
                    "longitude": 80.3211,
                    "description": "Terminal Gate 7 container freight station in North Chennai.",
                    "significance": "Smuggling entry point for Compound-9 precursor.",
                },
                {
                    "location_id": "LOC-002",
                    "name": "Parthiban Cafe & Residence",
                    "state": "Himachal Pradesh",
                    "latitude": 31.1218,
                    "longitude": 77.3512,
                    "description": "Quiet bakery and cafe in Theog, Shimla district.",
                    "significance": "Site of midnight hit squad attack and arson.",
                },
                {
                    "location_id": "LOC-003",
                    "name": "Nellore Transport Yard",
                    "state": "Andhra Pradesh",
                    "latitude": 14.4426,
                    "longitude": 79.9865,
                    "description": "Heavy truck maintenance yard near AP-TN border.",
                    "significance": "Ambush site where Anbu confronted Dilli.",
                },
                {
                    "location_id": "LOC-004",
                    "name": "Ranipet Ceramic Factory",
                    "state": "Tamil Nadu",
                    "latitude": 12.9279,
                    "longitude": 79.3330,
                    "description": "Abandoned industrial tile manufacturing facility.",
                    "significance": "Convergence point of Leo, Dilli, Vikram and siege battle.",
                },
                {
                    "location_id": "LOC-005",
                    "name": "Royapuram Coal Berth 11",
                    "state": "Tamil Nadu",
                    "latitude": 13.1147,
                    "longitude": 80.2981,
                    "description": "Dock terminal at Chennai Port berthed with MV Scorpia.",
                    "significance": "Final showdown; death of Rolex and burning of refinery.",
                },
                {
                    "location_id": "LOC-006",
                    "name": "Sandy Nullah Industrial Unit",
                    "state": "Tamil Nadu",
                    "latitude": 11.4510,
                    "longitude": 76.6430,
                    "description": "Former Das & Co. distillery and pharmaceutical factory in Nilgiris.",
                    "significance": "Original synthesis site of Compound-9 in 2004.",
                },
            ],
            "access_logs": [
                {
                    "log_id": "ACC-801",
                    "card_or_badge_id": "Card #4419",
                    "user_name": "ACP Stephen Raj",
                    "facility_location": "State OCIU Evidence Vault",
                    "access_timestamp": "2024-03-16 19:40:00+05:30",
                    "action_description": "Retrieved sealed 2018 Das & Co case files and transit logs.",
                },
                {
                    "log_id": "ACC-802",
                    "card_or_badge_id": "ADMIN-01",
                    "user_name": "Port Master Terminal",
                    "facility_location": "Ennore Port CFS-4 Gate 7",
                    "access_timestamp": "2024-03-14 02:35:00+05:30",
                    "action_description": "Gate 7 boom barrier bypassed for container truck TN-04-E-8819.",
                },
                {
                    "log_id": "ACC-803",
                    "card_or_badge_id": "Badge #9011",
                    "user_name": "Chief Eng. MV Scorpia",
                    "facility_location": "MV Scorpia Hold 3",
                    "access_timestamp": "2024-04-06 01:10:00+05:30",
                    "action_description": "Access granted to Hold 3 / Central Chemical Conversion Lab.",
                },
                {
                    "log_id": "ACC-804",
                    "card_or_badge_id": "Card #1088",
                    "user_name": "Constable Murugan",
                    "facility_location": "Vellore Central Prison Escort",
                    "access_timestamp": "2024-03-12 04:15:00+05:30",
                    "action_description": "Medical escort authorization signed for Adaikalam transfer.",
                },
                {
                    "log_id": "ACC-805",
                    "card_or_badge_id": "Badge #2204",
                    "user_name": "Inspector Joshy",
                    "facility_location": "Theog Police Station Armory",
                    "access_timestamp": "2024-03-21 17:00:00+05:30",
                    "action_description": "Routine weapon inventory check; no ammunition missing.",
                },
            ],
            "vehicle_records": [
                {
                    "vehicle_id": "VEH-301",
                    "registration_number": "TN-04-E-8819",
                    "vehicle_type": "Ashok Leyland 16-Wheeler",
                    "registered_owner": "Scorpion Maritime Logistics",
                    "sighting_location": "Ennore Port CFS-4",
                    "sighting_timestamp": "2024-03-14 02:40:00+05:30",
                },
                {
                    "vehicle_id": "VEH-302",
                    "registration_number": "AP-26-BK-9009",
                    "vehicle_type": "Mahindra Scorpio (Black)",
                    "registered_owner": "Anbu",
                    "sighting_location": "Nellore Highway Toll Plaza",
                    "sighting_timestamp": "2024-03-18 21:50:00+05:30",
                },
                {
                    "vehicle_id": "VEH-303",
                    "registration_number": "HP-01-AA-4040",
                    "vehicle_type": "Mahindra Bolero Camper",
                    "registered_owner": "Parthiban",
                    "sighting_location": "Chandigarh-Shimla Highway",
                    "sighting_timestamp": "2024-03-22 03:30:00+05:30",
                },
                {
                    "vehicle_id": "VEH-304",
                    "registration_number": "TN-23-CC-1100",
                    "vehicle_type": "Tata 407 Armored Transport",
                    "registered_owner": "Viper Selvam",
                    "sighting_location": "Ranipet Industrial Gate",
                    "sighting_timestamp": "2024-04-05 00:05:00+05:30",
                },
                {
                    "vehicle_id": "VEH-305",
                    "registration_number": "TN-09-AX-5521",
                    "vehicle_type": "Toyota Fortuner (White)",
                    "registered_owner": "ACP Stephen Raj",
                    "sighting_location": "OCIU Chennai Headquarters",
                    "sighting_timestamp": "2024-04-04 20:15:00+05:30",
                },
            ],
            "phone_records": [
                {
                    "call_id": "TEL-501",
                    "caller_imsi": "404-45-89102482",
                    "receiver_imsi": "404-71-11928340",
                    "caller_name": "Rolex",
                    "receiver_name": "Rover Unit-4 (Shimla)",
                    "call_timestamp": "2024-03-14 03:15:00+05:30",
                    "duration_seconds": 42,
                    "cell_tower": "Ennore-North",
                    "notes": "Rolex orders hit on Leo Das in Theog to recover the cold ledger.",
                },
                {
                    "call_id": "TEL-502",
                    "caller_imsi": "404-98-33019284",
                    "receiver_imsi": "404-11-00998822",
                    "caller_name": "Dilli",
                    "receiver_name": "Agent Vikram",
                    "call_timestamp": "2024-03-18 22:34:00+05:30",
                    "duration_seconds": 115,
                    "cell_tower": "Nellore-South",
                    "notes": "Dilli alerts Vikram after surviving Anbu ambush in Nellore.",
                },
                {
                    "call_id": "TEL-503",
                    "caller_imsi": "404-22-77610293",
                    "receiver_imsi": "404-45-89102482",
                    "caller_name": "ACP Stephen Raj",
                    "receiver_name": "Rolex",
                    "call_timestamp": "2024-04-04 23:52:00+05:30",
                    "duration_seconds": 28,
                    "cell_tower": "Ranipet-Ind-2",
                    "notes": "Stephen Raj confirms target presence inside Ranipet Tile Works.",
                },
                {
                    "call_id": "TEL-504",
                    "caller_imsi": "404-11-00998822",
                    "receiver_imsi": "SAT-LINK-8830",
                    "caller_name": "Agent Vikram",
                    "receiver_name": "Tactical Outpost",
                    "call_timestamp": "2024-04-06 02:28:00+05:30",
                    "duration_seconds": 15,
                    "cell_tower": "Royapuram-Pier",
                    "notes": "Vikram coordinates Royapuram Port master electrical blackout.",
                },
            ],
            "messages": [
                {
                    "message_id": "MSG-01",
                    "sender": "404-45-89102482",
                    "receiver": "404-88-29103940",
                    "sent_timestamp": "2024-03-15 08:20:00+05:30",
                    "message_text": "Theog coordinates verified. Bring the Nilgiris ledger intact. Burn the rest.",
                    "encryption_type": "AES-256",
                },
                {
                    "message_id": "MSG-02",
                    "sender": "404-22-77610293",
                    "receiver": "404-45-89102482",
                    "sent_timestamp": "2024-04-04 23:50:00+05:30",
                    "message_text": "Target is in Ranipet Tile Works. 5 men inside. Close the perimeter now.",
                    "encryption_type": "Plaintext SMS",
                },
                {
                    "message_id": "MSG-03",
                    "sender": "SAT-LINK-01",
                    "receiver": "FIELD-UNIT-AMAR",
                    "sent_timestamp": "2024-04-06 02:15:00+05:30",
                    "message_text": "Blackout confirmed at 02:30. Weapons free on all perimeter targets.",
                    "encryption_type": "Quantum Sat-Relay",
                },
                {
                    "message_id": "MSG-04",
                    "sender": "404-71-11928340",
                    "receiver": "404-45-89102482",
                    "sent_timestamp": "2024-03-22 01:40:00+05:30",
                    "message_text": "Cafe breached. Sanjeev down. Target is heading south.",
                    "encryption_type": "AES-256",
                },
            ],
            "bank_transactions": [
                {
                    "transaction_id": "TXN-901",
                    "sender_account": "Scorpion Maritime Corp (Panama)",
                    "receiver_account": "Sanjeev Kumar (HDFC Shimla)",
                    "amount": 5000000.00,
                    "transaction_type": "Wire Transfer",
                    "reference_number": "SWIFT-SCORP-9910",
                    "transaction_timestamp": "2024-03-16 11:30:00+05:30",
                },
                {
                    "transaction_id": "TXN-902",
                    "sender_account": "Hawala DXB Hub (Dubai)",
                    "receiver_account": "SR-77 (Stephen Raj)",
                    "amount": 20000000.00,
                    "transaction_type": "Hawala Payout",
                    "reference_number": "HWL-DXB-44102",
                    "transaction_timestamp": "2024-04-02 16:45:00+05:30",
                },
                {
                    "transaction_id": "TXN-903",
                    "sender_account": "Parthiban (SB-77192-01)",
                    "receiver_account": "Cash Withdrawal (SBI Theog)",
                    "amount": 2000000.00,
                    "transaction_type": "Cash Withdrawal",
                    "reference_number": "ATM-THG-0021",
                    "transaction_timestamp": "2024-03-22 06:15:00+05:30",
                },
                {
                    "transaction_id": "TXN-904",
                    "sender_account": "Das & Co Legacy Reserve",
                    "receiver_account": "Scorpion Maritime Corp",
                    "amount": 150000000.00,
                    "transaction_type": "Automated Escrow",
                    "reference_number": "ESC-DAS-2004-99",
                    "transaction_timestamp": "2024-03-14 02:00:00+05:30",
                },
            ],
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "item_name": "32mm Drop-Forged Steel Wheel Spanner",
                    "recovered_location": "Nellore Transport Yard",
                    "recovery_timestamp": "2024-03-19 08:00:00+05:30",
                    "forensic_summary": "Heavy tool with epidermal tissue belonging to Anbu; bone fractures on cartel shooters.",
                    "matching_suspect": "Dilli",
                },
                {
                    "evidence_id": "EVD-002",
                    "item_name": "12 Spent 9x19mm Shell Casings (Hydra-Shok)",
                    "recovered_location": "Theog Cafe, HP",
                    "recovery_timestamp": "2024-03-22 09:30:00+05:30",
                    "forensic_summary": "Parabellum casings with firing pin impressions matching a customized Glock-19.",
                    "matching_suspect": "Parthiban (Leo Das)",
                },
                {
                    "evidence_id": "EVD-003",
                    "item_name": "Autopsy: Crushed Hyoid Bone & Thoracic Trauma",
                    "recovered_location": "Ranipet Ceramic Factory",
                    "recovery_timestamp": "2024-04-05 06:00:00+05:30",
                    "forensic_summary": "Fatal tracheal collapse caused by blunt-force crowbar impact in kiln bay.",
                    "matching_suspect": "Dilli",
                },
                {
                    "evidence_id": "EVD-004",
                    "item_name": "Damascus Steel Folding Blade",
                    "recovered_location": "MV Scorpia Hold 3",
                    "recovery_timestamp": "2024-04-06 06:00:00+05:30",
                    "forensic_summary": "Custom blade bearing Rolex fingerprint profile and apple fruit residue.",
                    "matching_suspect": "Rolex",
                },
                {
                    "evidence_id": "EVD-005",
                    "item_name": "Sealed Encrypted Flash Drive",
                    "recovered_location": "MV Scorpia Bridge Deck",
                    "recovery_timestamp": "2024-04-06 06:15:00+05:30",
                    "forensic_summary": "Contains offshore banking routing, state police informant rosters, and wire logs.",
                    "matching_suspect": "ACP Stephen Raj",
                },
                {
                    "evidence_id": "EVD-006",
                    "item_name": "Hand-Forged Curved Kukri Knife",
                    "recovered_location": "MV Scorpia Central Hold",
                    "recovery_timestamp": "2024-04-06 06:30:00+05:30",
                    "forensic_summary": "Heavy steel kukri blade matching fatal thoracic puncture wound on Rolex.",
                    "matching_suspect": "Parthiban (Leo Das)",
                },
            ],
            "characters": [
                {
                    "character_id": "CHAR-001",
                    "full_name": "Parthiban / Leo Das",
                    "alias": "Leo Das",
                    "primary_role": "Cafe Owner & Former Das & Co Enforcer",
                    "location_base": "Theog, Himachal Pradesh",
                    "organization": "Independent / Das & Co Legacy",
                    "status": "Alive",
                },
                {
                    "character_id": "CHAR-002",
                    "full_name": "Rolex",
                    "alias": "Rolex Sir",
                    "primary_role": "Supreme Syndicate Kingpin",
                    "location_base": "Offshore / Chennai Port",
                    "organization": "Global Narcotics Syndicate",
                    "status": "Deceased",
                },
                {
                    "character_id": "CHAR-003",
                    "full_name": "Agent Vikram",
                    "alias": "Karnan / Commander",
                    "primary_role": "Leader of Aarambam Black-Ops",
                    "location_base": "Shadow Safehouse Network",
                    "organization": "Aarambam Syndicate",
                    "status": "Alive",
                },
                {
                    "character_id": "CHAR-004",
                    "full_name": "Dilli",
                    "alias": "Dilli",
                    "primary_role": "Agricultural Truck Driver",
                    "location_base": "Nellore, Andhra Pradesh",
                    "organization": "Independent / Kaithi Veteran",
                    "status": "Alive",
                },
                {
                    "character_id": "CHAR-005",
                    "full_name": "Amar",
                    "alias": "Amar",
                    "primary_role": "Black-Ops Field Operative",
                    "location_base": "Bangalore / Chennai Hub",
                    "organization": "Aarambam Syndicate",
                    "status": "Alive",
                },
                {
                    "character_id": "CHAR-006",
                    "full_name": "Napoleon",
                    "alias": "Constable Napoleon",
                    "primary_role": "Communications & Safehouse Logistics",
                    "location_base": "Trichy / Ranipet Safehouse",
                    "organization": "Aarambam Syndicate",
                    "status": "Alive",
                },
                {
                    "character_id": "CHAR-007",
                    "full_name": "Adaikalam",
                    "alias": "Adaikalam",
                    "primary_role": "Cartel Transit Lieutenant",
                    "location_base": "Vellore / Ranipet",
                    "organization": "Rolex Syndicate",
                    "status": "Deceased",
                },
                {
                    "character_id": "CHAR-008",
                    "full_name": "Anbu",
                    "alias": "Anbu",
                    "primary_role": "Cartel Enforcer",
                    "location_base": "Nellore / Chennai Port",
                    "organization": "Rolex Syndicate",
                    "status": "Deceased",
                },
                {
                    "character_id": "CHAR-009",
                    "full_name": "Viper Selvam",
                    "alias": "Selvam",
                    "primary_role": "Chemical Broker & Strike Commander",
                    "location_base": "Chennai / Ranipet",
                    "organization": "Scorpion Maritime Logistics",
                    "status": "Deceased",
                },
                {
                    "character_id": "CHAR-010",
                    "full_name": "K. Stephen Raj",
                    "alias": "ACP Stephen Raj",
                    "primary_role": "Corrupt Senior Intelligence Officer",
                    "location_base": "OCIU Headquarters Chennai",
                    "organization": "State Intelligence (Compromised)",
                    "status": "Deceased",
                },
                {
                    "character_id": "CHAR-011",
                    "full_name": "Sanjeev Kumar",
                    "alias": "Deputy Sanjeev",
                    "primary_role": "Rogue Deputy Inspector",
                    "location_base": "Theog Police Station",
                    "organization": "Local Police (Compromised)",
                    "status": "Deceased",
                },
            ],
            "relationships": [
                {
                    "relationship_id": "REL-01",
                    "person_a": "Antony Das",
                    "person_b": "Leo Das",
                    "relationship_type": "Father-Son",
                    "details": "Antony Das created Compound-9; killed during Theog clash in 2023.",
                },
                {
                    "relationship_id": "REL-02",
                    "person_a": "Harold Das",
                    "person_b": "Rolex",
                    "relationship_type": "Business Partners",
                    "details": "Harold promised Rolex the northern precursor corridor in 2018 before fallout.",
                },
                {
                    "relationship_id": "REL-03",
                    "person_a": "Adaikalam",
                    "person_b": "Anbu",
                    "relationship_type": "Brothers",
                    "details": "Syndicate regional leaders operating under Rolex supervision.",
                },
                {
                    "relationship_id": "REL-04",
                    "person_a": "Dilli",
                    "person_b": "Amudha",
                    "relationship_type": "Father-Daughter",
                    "details": "Dilli fought through the 2019 siege to reunite with his daughter.",
                },
                {
                    "relationship_id": "REL-05",
                    "person_a": "Agent Vikram",
                    "person_b": "Amar",
                    "relationship_type": "Commander-Operative",
                    "details": "Core operatives of Aarambam tactical anti-cartel wing.",
                },
            ],
            "timeline_events": [
                {
                    "event_code": "EVT-101",
                    "occurred_at": "2024-03-14 02:40:00+05:30",
                    "location_name": "Ennore Port CFS-4",
                    "title": "Ghost Shipment Arrival",
                    "summary": "Truck TN-04-E-8819 clears customs with 12 cylinders of Compound-9.",
                    "key_individuals": "Rolex, Viper Selvam, Stephen Raj",
                },
                {
                    "event_code": "EVT-102",
                    "occurred_at": "2024-03-18 22:15:00+05:30",
                    "location_name": "Nellore Transport Yard",
                    "title": "Ambush on Dilli",
                    "summary": "Anbu ambushes Dilli for the 2019 ledger; Dilli fights off hit team and calls Vikram.",
                    "key_individuals": "Dilli, Anbu",
                },
                {
                    "event_code": "EVT-103",
                    "occurred_at": "2024-03-22 01:10:00+05:30",
                    "location_name": "Theog Cafe, HP",
                    "title": "Attack on Parthiban Cafe",
                    "summary": "12-man cartel hit squad breaches cafe; Parthiban eliminates squad and interrogates Sanjeev.",
                    "key_individuals": "Parthiban, Sanjeev",
                },
                {
                    "event_code": "EVT-104",
                    "occurred_at": "2024-04-04 23:45:00+05:30",
                    "location_name": "Ranipet Ceramic Factory",
                    "title": "Convergence & Safehouse Leak",
                    "summary": "Leo, Dilli, Vikram, Amar, and Napoleon unite; Stephen Raj leaks GPS to cartel.",
                    "key_individuals": "Vikram, Leo, Dilli, Stephen Raj",
                },
                {
                    "event_code": "EVT-105",
                    "occurred_at": "2024-04-05 00:38:00+05:30",
                    "location_name": "Ranipet Ceramic Factory",
                    "title": "Adaikalam Executed",
                    "summary": "Dilli corners Adaikalam in Kiln 3 and crushes his windpipe with steel crowbar.",
                    "key_individuals": "Dilli, Adaikalam",
                },
                {
                    "event_code": "EVT-106",
                    "occurred_at": "2024-04-05 00:44:00+05:30",
                    "location_name": "Ranipet Boiler Room",
                    "title": "Viper Selvam Executed",
                    "summary": "Leo Das interrogates Viper Selvam, discovers MV Scorpia coordinates, and snaps his neck.",
                    "key_individuals": "Leo Das, Viper Selvam",
                },
                {
                    "event_code": "EVT-107",
                    "occurred_at": "2024-04-06 02:58:00+05:30",
                    "location_name": "MV Scorpia Bridge Deck",
                    "title": "ACP Stephen Raj Executed",
                    "summary": "Amar shoots Stephen Raj center-mass and secures encrypted flash drive.",
                    "key_individuals": "Amar, Stephen Raj",
                },
                {
                    "event_code": "EVT-108",
                    "occurred_at": "2024-04-06 03:05:00+05:30",
                    "location_name": "MV Scorpia Ballast Corridor",
                    "title": "Anbu Executed",
                    "summary": "Dilli strangles Anbu with heavy mooring chain in ballast corridor.",
                    "key_individuals": "Dilli, Anbu",
                },
                {
                    "event_code": "EVT-109",
                    "occurred_at": "2024-04-06 03:18:00+05:30",
                    "location_name": "MV Scorpia Central Hold",
                    "title": "Rolex Executed",
                    "summary": "Leo Das battles Rolex and drives a kukri knife through his chest.",
                    "key_individuals": "Leo Das, Rolex",
                },
            ],
            "red_herrings": [
                {
                    "record_id": "RED-01",
                    "lead_code": "RED-SHIMLA-LEAK",
                    "apparent_theory": "Initial intelligence suggested Inspector Joshy sold out Parthiban to the cartel.",
                    "forensic_truth": "Inspector Joshy was innocent; his junior Sanjeev stole case files after ₹50,00,000 wire from Panama.",
                    "debunking_evidence": "Bank transaction TXN-901 confirmed payout directly to Sanjeev Kumar.",
                },
                {
                    "record_id": "RED-02",
                    "lead_code": "RED-NELLORE-DURAI",
                    "apparent_theory": "OCIU intelligence files claimed Dilli was a kingpin operating under alias Nellore Durai.",
                    "forensic_truth": "Fabricated paperwork forged by Stephen Raj to justify a staged police encounter.",
                    "debunking_evidence": "Sealed flash drive EVD-005 found on Stephen Raj contained fake template dossiers.",
                },
                {
                    "record_id": "RED-03",
                    "lead_code": "RED-SANDY-NULLAH",
                    "apparent_theory": "Old news reports from 2004 claimed all Compound-9 stocks were destroyed in a factory fire.",
                    "forensic_truth": "Harold Das secretly relocated 500L to a dormant automated cold storage unit in Theog.",
                    "debunking_evidence": "Automated shipment SHP-401 dispatched Compound-9 from Theog 20 years later.",
                },
            ],
            "autopsies": [
                {
                    "autopsy_id": "AUT-01",
                    "victim_name": "Sanjeev Kumar",
                    "time_of_death": "2024-03-22 01:25:00+05:30",
                    "location_found": "Theog Cafe Hearth, HP",
                    "cause_of_death": "Single 9mm gunshot to head",
                    "killer_name": "Parthiban (Leo Das)",
                    "motive": "Betrayal / Leaking family location to cartel",
                },
                {
                    "autopsy_id": "AUT-02",
                    "victim_name": "Adaikalam",
                    "time_of_death": "2024-04-05 00:38:00+05:30",
                    "location_found": "Ranipet Factory Kiln 3, TN",
                    "cause_of_death": "32mm steel crowbar / Tracheal crush",
                    "killer_name": "Dilli",
                    "motive": "Self-defense / Protecting daughter Amudha",
                },
                {
                    "autopsy_id": "AUT-03",
                    "victim_name": "Viper Selvam",
                    "time_of_death": "2024-04-05 00:44:00+05:30",
                    "location_found": "Ranipet Boiler Room, TN",
                    "cause_of_death": "Manual Cervical Dislocation (Neck Snap)",
                    "killer_name": "Parthiban (Leo Das)",
                    "motive": "Interrogation / Eradicating Rolex strike commander",
                },
                {
                    "autopsy_id": "AUT-04",
                    "victim_name": "ACP K. Stephen Raj",
                    "time_of_death": "2024-04-06 02:58:00+05:30",
                    "location_found": "MV Scorpia Bridge Deck",
                    "cause_of_death": "Two 9x19mm rounds to chest (SIG Sauer MCX)",
                    "killer_name": "Amar",
                    "motive": "Eliminating cartel mole inside State Intelligence",
                },
                {
                    "autopsy_id": "AUT-05",
                    "victim_name": "Anbu",
                    "time_of_death": "2024-04-06 03:05:00+05:30",
                    "location_found": "MV Scorpia Ballast Corridor",
                    "cause_of_death": "Heavy industrial mooring chain strangulation",
                    "killer_name": "Dilli",
                    "motive": "Self-defense / Avenging harassment of family",
                },
                {
                    "autopsy_id": "AUT-06",
                    "victim_name": "Rolex",
                    "time_of_death": "2024-04-06 03:18:00+05:30",
                    "location_found": "MV Scorpia Central Hold",
                    "cause_of_death": "Hand-forged Kukri blade through thoracic cavity",
                    "killer_name": "Leo Das",
                    "motive": "Protecting family / Terminating Das & Co drug legacy",
                },
            ],
            "kill_records": [
                {
                    "record_id": "KIL-01",
                    "victim": "Sanjeev Kumar",
                    "killer": "Parthiban (Leo Das)",
                    "weapon": "Glock-19 (9x19mm)",
                    "date_time": "2024-03-22 01:25:00+05:30",
                    "location": "Theog Cafe, HP",
                    "plot_impact": "Eliminates Rolex intelligence arm in Himachal.",
                },
                {
                    "record_id": "KIL-02",
                    "victim": "Adaikalam",
                    "killer": "Dilli",
                    "weapon": "32mm Steel Crowbar",
                    "date_time": "2024-04-05 00:38:00+05:30",
                    "location": "Ranipet Factory Kiln 3, TN",
                    "plot_impact": "Closes the Kaithi syndicate chapter forever.",
                },
                {
                    "record_id": "KIL-03",
                    "victim": "Viper Selvam",
                    "killer": "Parthiban (Leo Das)",
                    "weapon": "Manual Cervical Dislocation",
                    "date_time": "2024-04-05 00:44:00+05:30",
                    "location": "Ranipet Boiler Room, TN",
                    "plot_impact": "Reveals location of MV Scorpia and the port lab.",
                },
                {
                    "record_id": "KIL-04",
                    "victim": "ACP K. Stephen Raj",
                    "killer": "Amar",
                    "weapon": "SIG Sauer MCX (9mm)",
                    "date_time": "2024-04-06 02:58:00+05:30",
                    "location": "MV Scorpia Bridge Deck",
                    "plot_impact": "Yields encrypted flash drive with offshore accounts.",
                },
                {
                    "record_id": "KIL-05",
                    "victim": "Anbu",
                    "killer": "Dilli",
                    "weapon": "Mooring Chain",
                    "date_time": "2024-04-06 03:05:00+05:30",
                    "location": "MV Scorpia Ballast Corridor",
                    "plot_impact": "Completely wipes out Adaikalam bloodline.",
                },
                {
                    "record_id": "KIL-06",
                    "victim": "Rolex",
                    "killer": "Leo Das",
                    "weapon": "Hand-forged Kukri Blade",
                    "date_time": "2024-04-06 03:18:00+05:30",
                    "location": "MV Scorpia Central Hold",
                    "plot_impact": "Destroys apex leadership of South Asian cartel.",
                },
            ],
        }

    async def start_session(self, team_name: str) -> Session:
        cleaned = " ".join(team_name.split()).strip()
    async def get_or_create_participant(
        self,
        firebase_uid: str,
        email: str,
        display_name: str | None = None,
        photo_url: str | None = None,
        email_verified: bool = True,
    ) -> Participant:
        async with self._lock:
            # Check in-memory cache
            existing = self.participants.get(firebase_uid)
            if existing:
                existing.last_login_at = now_utc()
                if display_name:
                    existing.display_name = display_name
                if photo_url:
                    existing.photo_url = photo_url
                return existing

            # Check / Insert in Supabase if pool exists
            participant_id = str(uuid4())
            p = Participant(
                id=participant_id,
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
                email_verified=email_verified,
                is_qualified=False,
                created_at=now_utc(),
                last_login_at=now_utc(),
            )

            pool = await self.get_db_pool()
            if pool:
                try:
                    async with pool.acquire() as conn:
                        row = await conn.fetchrow(
                            """
                            insert into public.participants (id, firebase_uid, email, display_name, photo_url, email_verified, is_qualified, created_at, last_login_at)
                            values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            on conflict (firebase_uid) do update set
                                last_login_at = excluded.last_login_at,
                                display_name = coalesce(excluded.display_name, public.participants.display_name),
                                photo_url = coalesce(excluded.photo_url, public.participants.photo_url)
                            returning id, firebase_uid, email, display_name, photo_url, email_verified, is_qualified, created_at, last_login_at;
                            """,
                            p.id,
                            p.firebase_uid,
                            p.email,
                            p.display_name,
                            p.photo_url,
                            p.email_verified,
                            p.is_qualified,
                            p.created_at,
                            p.last_login_at,
                        )
                        if row:
                            p = Participant(
                                id=str(row["id"]),
                                firebase_uid=row["firebase_uid"],
                                email=row["email"],
                                display_name=row["display_name"],
                                photo_url=row["photo_url"],
                                email_verified=row["email_verified"],
                                is_qualified=row["is_qualified"],
                                created_at=row["created_at"],
                                last_login_at=row["last_login_at"],
                            )
                except Exception as exc:
                    logger.error(f"Error persisting participant to DB: {exc}")

            self.participants[firebase_uid] = p
            self.participants[p.id] = p
            return p

    def get_participant_by_firebase_uid(self, firebase_uid: str) -> Participant | None:
        return self.participants.get(firebase_uid)

    def get_participant_by_id(self, participant_id: str) -> Participant | None:
        return self.participants.get(participant_id)

    def get_participant_session(self, participant: Participant) -> Session | None:
        return next((s for s in self.sessions.values() if s.participant_id == participant.id), None)

    async def start_session(self, team_name: str, participant: Participant | None = None) -> Session:
        cleaned = team_name.strip() if team_name else ""
        if not cleaned:
            if participant and participant.display_name:
                cleaned = participant.display_name
            elif participant and participant.email:
                cleaned = participant.email.split("@")[0]
            else:
                raise GameError("Enter a team name to begin.", 422, "team_name_required")
        if len(cleaned) > 80:
            cleaned = cleaned[:80]

        async with self._lock:
            # 1. Check if this authenticated participant already has an active or completed session
            if participant:
                for s in self.sessions.values():
                    if s.participant_id == participant.id:
                        return s

            session_id = str(uuid4())
            session = Session(
                id=session_id,
                event_id=self.event.id,
                participant_id=participant.id if participant else None,
                team_name=cleaned,
                started_at=now_utc(),
                current_level_number=1 if self.levels else 0,
                quiz_passed=participant.is_qualified if participant else True,
            )
            self.sessions[session_id] = session

            # Optionally record into Supabase PostgreSQL if pool is available
            pool = await self.get_db_pool()
            if pool:
                try:
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            insert into public.game_sessions (id, event_id, participant_id, team_name, started_at, current_level_number, status)
                            values ($1, $2, $3, $4, $5, $6, 'IN_PROGRESS')
                            on conflict (id) do nothing
                            """,
                            session_id,
                            self.event.id,
                            participant.id if participant else None,
                            cleaned,
                            session.started_at,
                            session.current_level_number,
                        )
                except Exception as exc:
                    logger.error(f"Error persisting session to DB: {exc}")

            return session

    def get_session(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if not session:
            raise GameError("This investigation session could not be found.", 404, "session_not_found")
        return session

    def get_level_for_session(self, session: Session, level_id: str | None = None) -> Level | None:
        if level_id:
            level = next((item for item in self.levels if item.id == level_id), None)
        else:
            level = next((item for item in self.levels if item.level_number == session.current_level_number), None)
        if level and level.level_number > session.current_level_number:
            raise GameError("That level is still locked.", 403, "level_locked")
        return level

    def public_state(self, session: Session) -> dict[str, Any]:
        active_levels = [level for level in self.levels if level.active]
        current_level = self.get_level_for_session(session)
        lock_remaining = 0
        if session.last_submission_at:
            elapsed = (now_utc() - session.last_submission_at).total_seconds()
            lock_remaining = max(0, self.event.config.wrong_answer_lock_seconds - int(elapsed))

        level_hints = [
            {
                "id": hint.id,
                "title": hint.title,
                "penalty_minutes": hint.penalty_minutes,
                "unlocked": hint.id in session.used_hint_ids,
                "body": hint.body if hint.id in session.used_hint_ids else None,
            }
            for hint in self.hints
            if current_level and hint.level_id == current_level.id
        ]

        part = self.get_participant_by_id(session.participant_id) if session.participant_id else None

        return {
            "session_id": session.id,
            "event": {
                "name": self.event.name,
                "slug": self.event.slug,
                "tagline": self.event.tagline,
                "description": self.event.description,
                "disclaimer": self.event.story.disclaimer,
                "status": self.event.status,
            },
            "team_name": session.team_name,
            "participant": {
                "id": part.id,
                "email": part.email,
                "display_name": part.display_name,
                "photo_url": part.photo_url,
                "is_qualified": part.is_qualified or session.quiz_passed,
            } if part else None,
            "quiz_passed": session.quiz_passed or (part.is_qualified if part else True),
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "finish_at": session.finish_at.isoformat() if session.finish_at else None,
            "current_level_number": session.current_level_number,
            "total_levels": len(active_levels),
            "completed_levels": len(session.completed_level_numbers),
            "actual_duration_seconds": session.actual_duration_seconds,
            "wrong_submission_count": session.wrong_submission_count,
            "wrong_penalty_seconds": session.wrong_penalty_seconds,
            "hint_penalty_seconds": session.hint_penalty_seconds,
            "effective_time_seconds": session.effective_time_seconds,
            "submission_lock_remaining_seconds": lock_remaining,
            "has_configured_case": bool(active_levels),
            "hints": level_hints,
            "current_level": (
                {
                    "id": current_level.id,
                    "level_number": current_level.level_number,
                    "title": current_level.title,
                    "narrative_context": current_level.narrative_context,
                    "objective": current_level.objective,
                    "clue": current_level.clue,
                    "answer_type": current_level.answer_type,
                }
                if current_level
                else None
            ),
        }

    def visible_tables(self, session: Session) -> list[InvestigationTable]:
        lvl = max(session.current_level_number, 1)
        return [table for table in self.tables if table.visible and table.unlock_level <= lvl]

    def locked_table_count(self, session: Session) -> int:
        lvl = max(session.current_level_number, 1)
        return len([table for table in self.tables if table.visible and table.unlock_level > lvl])

    def validate_query(self, query: str, session: Session) -> str:
        if not query or not query.strip():
            raise GameError("Write a SELECT query before running it.", 422, "query_required")
        if len(query) > 12_000:
            raise GameError("Query is too long. Keep it under 12,000 characters.", 422, "query_too_long")

        # Strip SQL comments
        normalized = re.sub(r"/\*.*?\*/|--[^\n]*", " ", query, flags=re.S).strip()
        statements = [part.strip() for part in normalized.split(";") if part.strip()]
        if len(statements) != 1:
            raise GameError("Only one read-only statement can be run at a time.", 400, "single_statement_only")
        statement = statements[0]

        if not re.match(r"^(select|with)\b", statement, flags=re.I):
            raise GameError("Only read-only SELECT queries are allowed.", 403, "read_only_only")

        # Block dangerous operations
        forbidden = r"\b(drop|delete|update|insert|alter|truncate|create|grant|revoke|copy|execute|call|do|merge|comment|vacuum|set|reset)\b"
        if re.search(forbidden, statement, flags=re.I):
            raise GameError("That operation is not available in the investigation terminal.", 403, "operation_blocked")

        # Block protected system & management tables
        protected = r"\b(pg_catalog|information_schema|auth|storage|events|event_config|stories|game_levels|level_hints|level_tables|investigation_tables|game_sessions|game_progress|answer_submissions|hint_usage|query_logs|quiz_questions|quiz_options|quiz_attempts|leaderboard)\b"
        if re.search(protected, statement, flags=re.I):
            raise GameError("That table is protected and not accessible to participants.", 403, "table_protected")

        # Extract all referenced table names in FROM and JOIN clauses
        allowed = {table.name.lower() for table in self.visible_tables(session)}
        referenced = re.findall(
            r"\b(?:from|join)\s+([a-zA-Z_][\w$]*(?:\.[a-zA-Z_][\w$]*)?)",
            statement,
            flags=re.I,
        )
        for reference in referenced:
            table_name = reference.split(".")[-1].lower()
            # If it's a subquery alias or CTE or function call, it won't match a known table name,
            # but if it matches ANY known table from all tables that is locked, block it.
            all_known = {table.name.lower(): table for table in self.tables}
            if table_name in all_known and table_name not in allowed:
                raise GameError(
                    f"The table '{table_name}' is locked at your current level (unlocks at Level {all_known[table_name].unlock_level}).",
                    403,
                    "table_locked",
                )
        return statement

    async def execute_query(self, query: str, session: Session, max_rows: int) -> QueryResult:
        safe_query = self.validate_query(query, session)
        started = perf_counter()

        pool = await self.get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # Explicitly set search_path to investigation schema
                    await conn.execute("SET search_path TO investigation, public;")
                    # Run query with limit
                    stmt = f"SELECT * FROM ({safe_query}) AS _q LIMIT {max_rows};"
                    records = await conn.fetch(stmt)
                    if records:
                        columns = list(records[0].keys())
                        rows = [[_serialize_cell(val) for val in record.values()] for record in records]
                    else:
                        columns, rows = ["result"], []
                    duration_ms = max(1, int((perf_counter() - started) * 1000))
                    self._record_query_log(session.id, query, True, len(rows), duration_ms)
                    return QueryResult(columns, rows, len(rows), duration_ms)
            except Exception as exc:
                duration_ms = max(1, int((perf_counter() - started) * 1000))
                self._record_query_log(session.id, query, False, 0, duration_ms, str(exc))
                raise GameError(f"SQL Error: {exc}", 400, "sql_execution_error")

        # In-memory execution fallback using SQLite emulation or custom matcher
        columns, rows = self._execute_in_memory(safe_query, session, max_rows)
        duration_ms = max(1, int((perf_counter() - started) * 1000))
        self._record_query_log(session.id, query, True, len(rows), duration_ms)
        return QueryResult(columns, rows, len(rows), duration_ms)

    def _execute_in_memory(self, query: str, session: Session, max_rows: int) -> tuple[list[str], list[list[Any]]]:
        """In-memory SQLite emulator loaded with current unlocked investigation data."""
        import sqlite3

        conn = sqlite3.connect(":memory:")
        try:
            cur = conn.cursor()
            # Create unlocked tables in SQLite memory DB
            visible = self.visible_tables(session)
            for table in visible:
                data = self._local_data.get(table.name, [])
                if not table.columns:
                    continue

                def _sql_t(dt: str) -> str:
                    dt = dt.lower()
                    if "int" in dt:
                        return "INTEGER"
                    if "num" in dt or "dec" in dt or "float" in dt:
                        return "REAL"
                    return "TEXT"

                col_defs = ", ".join([f"{col.name} {_sql_t(col.data_type)}" for col in table.columns])
                cur.execute(f"CREATE TABLE {table.name} ({col_defs});")
                for row in data:
                    cols = [c.name for c in table.columns]
                    placeholders = ", ".join(["?"] * len(cols))
                    values = []
                    for c in table.columns:
                        raw_v = row.get(c.name)
                        if raw_v is None:
                            values.append(None)
                        elif "num" in c.data_type.lower() or "dec" in c.data_type.lower() or "float" in c.data_type.lower():
                            try:
                                values.append(float(raw_v))
                            except (ValueError, TypeError):
                                values.append(str(raw_v))
                        elif "int" in c.data_type.lower():
                            try:
                                values.append(int(raw_v))
                            except (ValueError, TypeError):
                                values.append(str(raw_v))
                        else:
                            values.append(str(raw_v))
                    cur.execute(f"INSERT INTO {table.name} ({', '.join(cols)}) VALUES ({placeholders});", values)

            # Rewrite postgres-specific syntax if any (e.g. ::text)
            sqlite_query = re.sub(r"::text\b", "", query, flags=re.I)
            cur.execute(sqlite_query)
            col_names = [d[0] for d in cur.description] if cur.description else ["result"]
            fetched = cur.fetchmany(max_rows)
            rows = [[_serialize_cell(c) for c in row] for row in fetched]
            return col_names, rows
        except sqlite3.Error as err:
            raise GameError(f"SQL Error: {err}", 400, "sql_execution_error")
        finally:
            conn.close()

    def _record_query_log(
        self,
        session_id: str,
        query: str,
        success: bool,
        row_count: int,
        duration_ms: int,
        error_code: str | None = None,
    ) -> None:
        self.query_logs.append(
            QueryLog(str(uuid4()), session_id, query, success, row_count, duration_ms)
        )

    async def submit_answer(self, session: Session, answer: str) -> dict[str, Any]:
        if session.status != "IN_PROGRESS":
            raise GameError("This investigation is already finished.", 409, "session_finished")
        if not self.levels:
            raise GameError("No investigation levels have been configured yet.", 409, "case_not_configured")

        # Check lock timer
        if session.last_submission_at:
            elapsed = (now_utc() - session.last_submission_at).total_seconds()
            remaining = self.event.config.wrong_answer_lock_seconds - int(elapsed)
            if remaining > 0:
                raise GameError(f"Answer submission locked. Try again in {remaining} seconds.", 429, "submission_locked")

        level = self.get_level_for_session(session)
        if not level:
            raise GameError("There is no active level for this session.", 409, "level_unavailable")

        submitted = answer.strip()
        if not submitted:
            raise GameError("Enter an answer before submitting.", 422, "answer_required")

        correct = self._compare_answer(level, submitted)
        penalty_seconds = 0
        lock_seconds = 0

        if correct:
            session.completed_level_numbers.add(level.level_number)
            next_level = next((item for item in self.levels if item.active and item.level_number > level.level_number), None)
            if next_level:
                session.current_level_number = next_level.level_number
            else:
                session.status = "COMPLETED"
                session.finish_at = now_utc()
        else:
            session.wrong_submission_count += 1
            penalty_seconds = self.event.config.wrong_answer_penalty_minutes * 60
            lock_seconds = self.event.config.wrong_answer_lock_seconds
            session.wrong_penalty_seconds += penalty_seconds
            session.last_submission_at = now_utc()

        self.answer_submissions.append(
            AnswerSubmission(str(uuid4()), session.id, level.id, submitted, correct, penalty_seconds, lock_seconds)
        )

        # Update database if connected
        pool = await self.get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        update public.game_sessions
                        set current_level_number = $1,
                            wrong_submission_count = $2,
                            wrong_penalty_seconds = $3,
                            status = $4,
                            finish_at = $5,
                            last_submission_at = $6
                        where id = $7;
                        """,
                        session.current_level_number,
                        session.wrong_submission_count,
                        session.wrong_penalty_seconds,
                        session.status,
                        session.finish_at,
                        session.last_submission_at,
                        session.id,
                    )
            except Exception as exc:
                logger.error(f"Failed to update session state in DB: {exc}")

        return {
            "correct": correct,
            "level_completed": correct,
            "next_level_unlocked": correct and session.status != "COMPLETED",
            "lock_seconds": lock_seconds,
            "penalty_seconds": penalty_seconds,
            "state": self.public_state(session),
        }

    def _compare_answer(self, level: Level, submitted: str) -> bool:
        normalized_sub = " ".join(submitted.strip().casefold().split())

        def clean_val(v: str) -> str:
            return " ".join(v.strip().casefold().split())

        if level.answer_type == "number":
            try:
                sub_float = float(submitted.strip())
                return any(sub_float == float(expected.strip()) for expected in level.answer_values)
            except ValueError:
                return False
        if level.answer_type == "exact":
            return submitted.strip() in level.answer_values

        expected_set = {clean_val(expected) for expected in level.answer_values}
        if normalized_sub in expected_set:
            return True

        # Handle split / compound answers like "Leo Das - Kukri" or "Parthiban - Kukri"
        for exp in level.answer_values:
            if "-" in exp and "-" in submitted:
                sub_parts = [p.strip().casefold() for p in submitted.split("-")]
                exp_parts = [p.strip().casefold() for p in exp.split("-")]
                if len(sub_parts) == len(exp_parts) and all(
                    sub_parts[i] in exp_parts[i] or exp_parts[i] in sub_parts[i] for i in range(len(sub_parts))
                ):
                    return True
        return False

    async def use_hint(self, session: Session, hint_id: str) -> dict[str, Any]:
        hint = next((item for item in self.hints if item.id == hint_id), None)
        if not hint:
            raise GameError("That hint is not available.", 404, "hint_not_found")
        curr_lvl = self.get_level_for_session(session)
        if not curr_lvl or hint.level_id != curr_lvl.id:
            raise GameError("That hint is not available at your current level.", 403, "hint_locked")
        if hint.id in session.used_hint_ids and not hint.repeatable:
            return {
                "hint_id": hint.id,
                "title": hint.title,
                "body": hint.body,
                "penalty_seconds": 0,
                "state": self.public_state(session),
            }

        session.used_hint_ids.add(hint.id)
        penalty = hint.penalty_minutes * 60
        session.hint_penalty_seconds += penalty

        # Update database if connected
        pool = await self.get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        update public.game_sessions
                        set hint_penalty_seconds = $1
                        where id = $2;
                        """,
                        session.hint_penalty_seconds,
                        session.id,
                    )
            except Exception as exc:
                logger.error(f"Failed to record hint penalty in DB: {exc}")

        return {
            "hint_id": hint.id,
            "title": hint.title,
            "body": hint.body,
            "penalty_seconds": penalty,
            "state": self.public_state(session),
        }

    def leaderboard(self) -> list[dict[str, Any]]:
        ranked = sorted(
            self.sessions.values(),
            key=lambda s: (
                0 if s.status == "COMPLETED" else 1,
                -s.current_level_number,
                s.effective_time_seconds,
            ),
        )
        total = len(self.levels)
        return [
            {
                "rank": index + 1,
                "team_name": session.team_name,
                "current_level": session.current_level_number,
                "total_levels": total,
                "progress_percent": round((len(session.completed_level_numbers) / total) * 100) if total else 0,
                "effective_time_seconds": session.effective_time_seconds,
                "status": session.status,
            }
            for index, session in enumerate(ranked)
        ]

    def get_quiz_questions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": q.id,
                "prompt": q.prompt,
                "points": q.points,
                "options": [{"id": opt.id, "option_text": opt.option_text} for opt in q.options],
            }
            for q in self.quiz_questions
        ]

    def evaluate_quiz(self, session_id: str, answers: dict[str, str]) -> dict[str, Any]:
        session = self.get_session(session_id)
        score = 0
        total = len(self.quiz_questions)
        for q in self.quiz_questions:
            chosen_opt_id = answers.get(q.id)
            correct_opt = next((o for o in q.options if o.is_correct), None)
            if correct_opt and chosen_opt_id == correct_opt.id:
                score += q.points

        qualify_score = self.event.config.quiz_qualify_score
        qualified = score >= qualify_score
        session.quiz_passed = qualified
        if session.participant_id:
            part = self.get_participant_by_id(session.participant_id)
            if part and qualified:
                part.is_qualified = True
        return {
            "score": score,
            "total_questions": total,
            "qualify_score": qualify_score,
            "qualified": qualified,
            "state": self.public_state(session),
        }