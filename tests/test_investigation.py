from __future__ import annotations

import asyncio
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.auth import create_session_jwt
from backend.app.main import app, store
from backend.app.models import Participant


def _mock_verify_token_ssn(id_token: str) -> dict:
    if id_token == "valid_ssn_token":
        return {
            "uid": "fb_ssn_user_001",
            "email": "sharruk2470048@ssn.edu.in",
            "email_verified": True,
            "name": "Sharruk SSN Detective",
            "picture": "https://example.com/photo.jpg",
        }
    elif id_token == "gmail_token":
        return {
            "uid": "fb_gmail_user_002",
            "email": "intruder@gmail.com",
            "email_verified": True,
            "name": "Gmail User",
        }
    elif id_token == "fake_subdomain_token":
        return {
            "uid": "fb_fake_user_003",
            "email": "hacker@ssn.edu.in.fake.com",
            "email_verified": True,
            "name": "Subdomain Impersonator",
        }
    elif id_token == "unverified_ssn_token":
        return {
            "uid": "fb_unverified_004",
            "email": "student@ssn.edu.in",
            "email_verified": False,
            "name": "Unverified Student",
        }
    elif id_token == "valid_ssn_token_2":
        return {
            "uid": "fb_ssn_user_002",
            "email": "detective_penalty@ssn.edu.in",
            "email_verified": True,
            "name": "Penalty Tester",
            "picture": "https://example.com/photo2.jpg",
        }
    raise ValueError("Invalid Firebase ID token.")


@pytest.mark.asyncio
async def test_firebase_auth_domain_restrictions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated access to game endpoints must fail (401)
        res = await client.post("/api/game/start", json={"team_name": "Ghost Team"})
        assert res.status_code == 401

        res = await client.post(
            "/api/query/execute",
            json={"session_id": "dummy", "query": "SELECT * FROM shipments;"},
        )
        assert res.status_code == 401

        # 2. Fake token / invalid token rejection
        with patch("firebase_admin.auth.verify_id_token", side_effect=Exception("Invalid signature")):
            res = await client.post("/api/auth/verify", json={"id_token": "malformed_token"})
            assert res.status_code == 401

        # 3. Non-SSN Gmail rejection
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("gmail_token")):
            res = await client.post("/api/auth/verify", json={"id_token": "gmail_token"})
            assert res.status_code == 403
            assert "only verified ssn" in res.json()["detail"]["message"].lower()

        # 4. Fake sub-domain rejection
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("fake_subdomain_token")):
            res = await client.post("/api/auth/verify", json={"id_token": "fake_subdomain_token"})
            assert res.status_code == 403
            assert "only verified ssn" in res.json()["detail"]["message"].lower()

        # 5. Unverified SSN account rejection
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("unverified_ssn_token")):
            res = await client.post("/api/auth/verify", json={"id_token": "unverified_ssn_token"})
            assert res.status_code == 403
            assert "verified" in res.json()["detail"]["message"].lower()

        # 6. Valid @ssn.edu.in account accepted
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("valid_ssn_token")):
            res = await client.post("/api/auth/verify", json={"id_token": "valid_ssn_token"})
            assert res.status_code == 200
            auth_data = res.json()
            assert "token" in auth_data
            assert auth_data["participant"]["email"] == "sharruk2470048@ssn.edu.in"
            session_id = auth_data["session"]["session_id"]

            # Same user verifying again gets the SAME session (prevents duplicate sessions / timer restart)
            res2 = await client.post("/api/auth/verify", json={"id_token": "valid_ssn_token"})
            assert res2.status_code == 200
            assert res2.json()["session"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_full_investigation_authenticated_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/api/health")
        assert res.status_code == 200
        health_data = res.json()
        assert health_data["status"] == "ok"
        assert health_data["story"] == "LCU: ECLIPSE"

        # 2. Authenticate as SSN detective
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("valid_ssn_token")):
            auth_res = await client.post("/api/auth/verify", json={"id_token": "valid_ssn_token"})
            assert auth_res.status_code == 200
            jwt_token = auth_res.json()["token"]
            session_data = auth_res.json()["session"]
            session_id = session_data["session_id"]

        headers = {"Authorization": f"Bearer {jwt_token}"}

        # 3. Security Tests
        # Test 3a: Block mutation operations
        mutations = [
            "DROP TABLE shipments;",
            "DELETE FROM shipments;",
            "UPDATE shipments SET declared_manifest = 'test';",
            "INSERT INTO shipments (shipment_id) VALUES ('x');",
            "ALTER TABLE shipments ADD COLUMN test text;",
            "TRUNCATE TABLE shipments;",
        ]
        for bad_sql in mutations:
            q_res = await client.post(
                "/api/query/execute",
                json={"session_id": session_id, "query": bad_sql},
                headers=headers,
            )
            assert q_res.status_code == 403, f"Expected 403 for mutation: {bad_sql}"

        # Test 3b: Block protected tables (answers, system tables)
        protected_queries = [
            "SELECT * FROM game_levels;",
            "SELECT * FROM answer_submissions;",
            "SELECT * FROM level_hints;",
            "SELECT * FROM event_config;",
            "SELECT * FROM pg_catalog.pg_tables;",
        ]
        for prot_sql in protected_queries:
            q_res = await client.post(
                "/api/query/execute",
                json={"session_id": session_id, "query": prot_sql},
                headers=headers,
            )
            assert q_res.status_code == 403, f"Expected 403 for protected table query: {prot_sql}"

        # Test 3c: Locked table enforcement at Level 1
        locked_query = "SELECT * FROM phone_records;"
        q_res = await client.post(
            "/api/query/execute",
            json={"session_id": session_id, "query": locked_query},
            headers=headers,
        )
        assert q_res.status_code == 403
        assert "locked" in q_res.json()["detail"]["message"].lower()

        # 4. Level 1: Ghost shipment at Ennore
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT container_number, declared_manifest FROM shipments WHERE destination LIKE '%Ennore%';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("MEDU-774910-2" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "MEDU-774910-2"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 2

        # 5. Level 2: Customs bypass override ID
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT card_or_badge_id FROM access_logs WHERE facility_location LIKE '%Gate 7%';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("ADMIN-01" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "ADMIN-01"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 3

        # 6. Level 3: Intercepting the command call
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT caller_imsi FROM phone_records WHERE cell_tower = 'Ennore-North';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("404-45-89102482" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "404-45-89102482"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 4

        # 7. Level 4: The corrupt deputy in Theog
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT receiver_account FROM bank_transactions WHERE amount = 5000000;",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("Sanjeev" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "Sanjeev Kumar"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 5

        # 8. Level 5: Ambush at Nellore yard
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT registration_number FROM vehicle_records WHERE sighting_location LIKE '%Nellore%';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("AP-26-BK-9009" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "AP-26-BK-9009"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 6

        # 9. Level 6: The State Intelligence mole
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT m.sender, m.message_text, p.caller_name FROM messages m JOIN phone_records p ON p.caller_imsi = m.sender WHERE m.message_text LIKE '%Ranipet%';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("Stephen Raj" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "ACP Stephen Raj"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 7

        # 10. Level 7: The Hawala trail
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT reference_number FROM bank_transactions WHERE receiver_account LIKE '%SR-77%';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("HWL-DXB-44102" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "HWL-DXB-44102"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 8

        # 11. Level 8: Autopsy of Viper Selvam
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT cause_of_death FROM autopsies WHERE victim_name = 'Viper Selvam';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("Cervical" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "Manual Cervical Dislocation"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 9

        # 12. Level 9: IMO number of MV Scorpia
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT imo_number FROM shipments WHERE vessel_name = 'MV Scorpia';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200
        assert any("9182344" in str(row) for row in q_res.json()["rows"])

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "9182344"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["current_level_number"] == 10

        # 13. Level 10: Final showdown - Who killed Rolex
        q_res = await client.post(
            "/api/query/execute",
            json={
                "session_id": session_id,
                "query": "SELECT killer_name, cause_of_death FROM autopsies WHERE victim_name = 'Rolex';",
            },
            headers=headers,
        )
        assert q_res.status_code == 200

        ans_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "Leo Das - Kukri"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["correct"] is True
        assert ans_res.json()["state"]["status"] == "COMPLETED"

        # 14. Leaderboard check
        lb_res = await client.get("/api/leaderboard")
        assert lb_res.status_code == 200
        entries = lb_res.json()["entries"]
        assert len(entries) >= 1
        assert entries[0]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_quiz_qualifier_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Authenticate
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("valid_ssn_token")):
            auth_res = await client.post("/api/auth/verify", json={"id_token": "valid_ssn_token"})
            jwt_token = auth_res.json()["token"]
            session_id = auth_res.json()["session"]["session_id"]

        headers = {"Authorization": f"Bearer {jwt_token}"}

        # Fetch quiz questions (public endpoint)
        q_res = await client.get("/api/quiz/questions")
        assert q_res.status_code == 200
        questions = q_res.json()["questions"]
        assert len(questions) == 5

        # Submit answers
        submit_res = await client.post(
            "/api/quiz/submit",
            json={
                "session_id": session_id,
                "answers": {"q1": "q1_1", "q2": "q2_1", "q3": "q3_1", "q4": "q4_1", "q5": "q5_1"},
            },
            headers=headers,
        )
        assert submit_res.status_code == 200
        res_data = submit_res.json()
        assert res_data["score"] == 5
        assert res_data["qualified"] is True


@pytest.mark.asyncio
async def test_hint_and_wrong_answer_penalties():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("firebase_admin.auth.verify_id_token", return_value=_mock_verify_token_ssn("valid_ssn_token_2")):
            auth_res = await client.post("/api/auth/verify", json={"id_token": "valid_ssn_token_2"})
            jwt_token = auth_res.json()["token"]
            session_id = auth_res.json()["session"]["session_id"]

        headers = {"Authorization": f"Bearer {jwt_token}"}

        # Test Hint penalty (+2 min / 120s)
        hint_res = await client.post(
            "/api/hint/use",
            json={"session_id": session_id, "hint_id": "h01"},
            headers=headers,
        )
        assert hint_res.status_code == 200
        assert hint_res.json()["penalty_seconds"] == 120
        assert hint_res.json()["state"]["hint_penalty_seconds"] == 120

        # Test Wrong Answer penalty (+5 min / 300s) and Lockout (60s)
        wrong_res = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "WRONG_ANSWER"},
            headers=headers,
        )
        assert wrong_res.status_code == 200
        assert wrong_res.json()["correct"] is False
        assert wrong_res.json()["penalty_seconds"] == 300
        assert wrong_res.json()["lock_seconds"] == 60
        assert wrong_res.json()["state"]["wrong_penalty_seconds"] == 300

        # Attempting submission immediately should be locked (429)
        lock_attempt = await client.post(
            "/api/answer/submit",
            json={"session_id": session_id, "answer": "ANOTHER_TRY"},
            headers=headers,
        )
        assert lock_attempt.status_code == 429
        assert "locked" in lock_attempt.json()["detail"]["message"].lower()
