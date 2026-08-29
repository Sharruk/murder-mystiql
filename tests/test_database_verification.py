from __future__ import annotations

import pytest
from pathlib import Path
from backend.app.store import GameStore

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_sql_files_exist_and_non_empty():
    schema_sql = ROOT_DIR / "database" / "schema.sql"
    migration_sql = ROOT_DIR / "database" / "migration_firebase_auth.sql"
    seed_sql = ROOT_DIR / "database" / "seed_lcu_eclipse.sql"
    setup_all_sql = ROOT_DIR / "database" / "setup_all.sql"

    for f in [schema_sql, migration_sql, seed_sql, setup_all_sql]:
        assert f.is_file(), f"Expected {f.name} to exist"
        content = f.read_text(encoding="utf-8")
        assert len(content) > 100, f"Expected {f.name} to have content"


def test_in_memory_store_contains_all_tables_and_rows():
    store = GameStore()
    assert len(store.levels) == 10
    assert len(store.tables) == 14
    assert len(store.hints) == 10
    assert len(store.quiz_questions) == 5

    expected_tables = [
        "shipments",
        "access_logs",
        "vehicle_records",
        "phone_records",
        "messages",
        "bank_transactions",
        "evidence",
        "characters",
        "locations",
        "timeline_events",
        "relationships",
        "red_herrings",
        "autopsies",
        "kill_records",
    ]

    for tbl in expected_tables:
        rows = store._local_data.get(tbl, [])
        assert len(rows) > 0, f"Table {tbl} must contain seeded records"


@pytest.mark.asyncio
async def test_all_10_level_queries_in_store():
    store = GameStore()
    session = await store.start_session("Test Team")
    # Grant max level visibility to test all queries
    session.current_level_number = 10

    queries = [
        # Level 1
        ("SELECT container_number, declared_manifest FROM shipments WHERE destination LIKE '%Ennore%' AND declared_manifest LIKE '%Industrial%';", "MEDU-774910-2"),
        # Level 2
        ("SELECT card_or_badge_id, action_description FROM access_logs WHERE facility_location LIKE '%Gate 7%';", "ADMIN-01"),
        # Level 3
        ("SELECT caller_imsi, notes FROM phone_records WHERE cell_tower = 'Ennore-North';", "404-45-89102482"),
        # Level 4
        ("SELECT receiver_account, amount, reference_number FROM bank_transactions WHERE sender_account LIKE '%Scorpion Maritime%' AND amount = 5000000;", "Sanjeev"),
        # Level 5
        ("SELECT registration_number, vehicle_type, registered_owner FROM vehicle_records WHERE sighting_location LIKE '%Nellore%';", "AP-26-BK-9009"),
        # Level 6
        ("SELECT m.sender, m.message_text, p.caller_name FROM messages m JOIN phone_records p ON p.caller_imsi = m.sender WHERE m.message_text LIKE '%Ranipet%';", "Stephen Raj"),
        # Level 7
        ("SELECT reference_number, amount FROM bank_transactions WHERE receiver_account LIKE '%SR-77%' AND amount = 20000000;", "HWL-DXB-44102"),
        # Level 8
        ("SELECT victim_name, cause_of_death, killer_name FROM autopsies WHERE victim_name = 'Viper Selvam';", "Cervical"),
        # Level 9
        ("SELECT imo_number, vessel_name FROM shipments WHERE vessel_name = 'MV Scorpia';", "9182344"),
        # Level 10
        ("SELECT k.victim, k.killer, k.weapon, k.location, k.plot_impact, a.cause_of_death FROM kill_records k JOIN autopsies a ON a.victim_name = k.victim WHERE k.victim = 'Rolex';", "Leo Das"),
    ]

    for sql, expected in queries:
        res = await store.execute_query(sql, session, 200)
        assert res.row_count > 0, f"Query returned 0 rows: {sql}"
        str_output = str(res.rows)
        assert expected in str_output, f"Expected {expected} in result of {sql}, got {str_output}"
