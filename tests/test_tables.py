
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tableturn.app import create_app
from tableturn.clock import get_clock
from tableturn.models import DiningTable
from tests.conftest import make_settings


def test_seeding_is_idempotent_across_two_starts(tmp_path, clock):
    settings = make_settings(tmp_path)

    for _ in range(2):
        app = create_app(settings)
        app.dependency_overrides[get_clock] = lambda: clock

        with TestClient(app) as c:
            assert c.get("/branches/Baner/tables").json()["free"] == 22

        with app.state.sessionmaker() as s:
            assert s.scalar(
                select(func.count()).select_from(DiningTable)
            ) == 22

        app.state.engine.dispose()


def test_floor_has_twenty_two_tables_all_free(client):
    r = client.get("/branches/Baner/tables")
    assert r.status_code == 200

    body = r.json()

    assert (
        body["branch"] == "Baner"
        and body["free"] == 22
        and len(body["tables"]) == 22
    )

    seats = [t["seats"] for t in body["tables"]]

    assert (
        seats.count(2) == 10
        and seats.count(4) == 8
        and seats.count(6) == 4
    )

    assert all(t["state"] == "free" for t in body["tables"])

    # A free table carries exactly the contract's keys — no party,
    # no seating, no null placeholders.
    assert all(
        set(t) == {"no", "seats", "section", "state"}
        for t in body["tables"]
    )

    assert {
        t["section"] for t in body["tables"]
    } == {"Window", "Garden", "Indoor"}


def test_section_filter_returns_only_that_section_and_its_free_count(client):
    r = client.get("/branches/Baner/tables?section=Garden")
    body = r.json()

    assert body["tables"] and all(
        t["section"] == "Garden"
        for t in body["tables"]
    )

    assert body["free"] == len(body["tables"]) == 8
