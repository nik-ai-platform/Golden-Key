from datetime import datetime

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.data.ncaaf_team_aliases import REVIEWED_CFBD_TEAM_MAPPINGS
from app.models.team import Team
from app.models.team_alias import TeamAlias
from app.providers.cfbd_client import CFBDClient
from app.services.team_identity_service import TeamIdentityService


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_cfbd_client_maps_factual_fields_and_nullable_neutral_site():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 44,
                    "season": 2025,
                    "startDate": "2025-09-06T19:30:00Z",
                    "homeId": 1,
                    "awayId": 2,
                    "homeTeam": "Home State",
                    "awayTeam": "Away Tech",
                    "homePoints": 31,
                    "awayPoints": 20,
                    "completed": True,
                    "neutralSite": None,
                    "venue": "Field",
                }
            ],
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://cfbd.test") as http_client:
        game = CFBDClient(api_key="secret", client=http_client).get_games(2025)[0]

    assert game.id == 44
    assert game.start_date == datetime(2025, 9, 6, 19, 30)
    assert game.neutral_site is None
    assert game.venue_name == "Field"
    assert game.venue_city is None
    assert game.home_points == 31.0


def test_cfbd_client_maps_team_and_season_metadata():
    responses = {
        "/teams": [
            {
                "id": 1,
                "school": "Home State",
                "alternateNames": ["Home St."],
                "abbreviation": "HST",
                "conference": "Alpha",
                "classification": "FBS",
                "division": "I-A",
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses[request.url.path])

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://cfbd.test",
    ) as http_client:
        client = CFBDClient(api_key="secret", client=http_client)
        team = client.get_teams(2025)[0]
        metadata = client.get_team_metadata(2025)[0]

    assert team.alternate_names == ("Home St.",)
    assert team.abbreviation == "HST"
    assert metadata.conference == "Alpha"
    assert metadata.classification == "FBS"
    assert metadata.is_fbs is True


def test_identity_resolution_prefers_provider_identity_and_normalizes_alias(db):
    team = Team(name="Miami (FL) Hurricanes", league="NCAAF", sport="NCAAF")
    db.add(team)
    db.flush()
    service = TeamIdentityService(db)
    assert service.add_alias(
        team_id=team.id,
        provider="cfbd",
        alias_name="Miami-FL",
    )
    db.flush()

    first = service.resolve(
        provider="cfbd",
        provider_team_id="test-miami",
        provider_name="Miami FL",
        sport="NCAAF",
        league="NCAAF",
    )
    second = service.resolve(
        provider="cfbd",
        provider_team_id="test-miami",
        provider_name="Miami Hurricanes",
        sport="NCAAF",
        league="NCAAF",
    )

    assert TeamIdentityService.normalize_name("Miami (FL)") == "miamifl"
    assert first.team.id == team.id
    assert first.method == "exact_alias"
    assert second.team.id == team.id
    assert second.method == "provider_identity"
    assert db.query(TeamAlias).count() == 1


def test_identity_resolution_rejects_ambiguous_canonical_names(db):
    db.add_all(
        [
            Team(name="St. Thomas", league="NCAAF", sport="NCAAF"),
            Team(name="St Thomas", league="NCAAF", sport="NCAAF"),
        ]
    )
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="999",
        provider_name="St-Thomas",
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.team is None
    assert result.is_ambiguous
    assert result.method == "unresolved"


@pytest.mark.parametrize(
    ("provider_name", "canonical_name"),
    [
        ("Alabama", "Alabama Crimson Tide"),
        ("Boston College", "Boston College Eagles"),
        ("Notre Dame", "Notre Dame Fighting Irish"),
        ("Air Force", "Air Force Falcons"),
    ],
)
def test_identity_resolution_matches_unique_mascot_suffix(
    db,
    provider_name,
    canonical_name,
):
    team = Team(name=canonical_name, league="NCAAF", sport="NCAAF")
    db.add(team)
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="1",
        provider_name=provider_name,
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.team.id == team.id
    assert result.method == "mascot_suffix"
    assert result.provider_name == provider_name
    assert result.canonical_name == canonical_name


def test_short_or_ambiguous_prefix_is_rejected(db):
    db.add_all(
        [
            Team(name="USC Trojans", league="NCAAF", sport="NCAAF"),
            Team(name="Oregon Ducks", league="NCAAF", sport="NCAAF"),
            Team(name="Oregon State Beavers", league="NCAAF", sport="NCAAF"),
        ]
    )
    db.flush()
    service = TeamIdentityService(db)

    short = service.resolve(
        provider="cfbd",
        provider_team_id="1",
        provider_name="USC",
        sport="NCAAF",
        league="NCAAF",
        allow_create=False,
    )
    ambiguous = service.resolve(
        provider="cfbd",
        provider_team_id="2",
        provider_name="Oregon",
        sport="NCAAF",
        league="NCAAF",
        allow_create=False,
    )

    assert short.team is None
    assert short.method == "unresolved"
    assert ambiguous.team is None
    assert ambiguous.is_ambiguous


def test_institutional_suffix_is_not_treated_as_mascot(db):
    db.add(Team(name="San Diego State Aztecs", league="NCAAF", sport="NCAAF"))
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="301",
        provider_name="San Diego",
        sport="NCAAF",
        league="NCAAF",
        allow_create=False,
    )

    assert result.team is None


def test_reviewed_alias_resolves_app_state(db):
    team = Team(name="Appalachian State Mountaineers", league="NCAAF", sport="NCAAF")
    db.add(team)
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="2026",
        provider_name="App State",
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.team.id == team.id
    assert result.method == "reviewed_alias"


def test_duplicate_alias_inputs_are_deduplicated_before_flush(db):
    team = Team(name="Alabama Crimson Tide", league="NCAAF", sport="NCAAF")
    db.add(team)
    db.flush()
    service = TeamIdentityService(db)

    assert service.add_alias(team_id=team.id, provider="cfbd", alias_name="Alabama")
    assert not service.add_alias(team_id=team.id, provider="cfbd", alias_name="Alabama")
    assert service.add_alias(team_id=team.id, provider="cfbd", alias_name="ALA")
    assert not service.add_alias(team_id=team.id, provider="cfbd", alias_name="A-L-A")
    db.flush()

    assert db.query(TeamAlias).count() == 2


def test_official_alternate_name_participates_in_exact_alias_matching(db):
    team = Team(name="Connecticut Huskies", league="NCAAF", sport="NCAAF")
    db.add(team)
    db.flush()
    db.add(
        TeamAlias(
            team_id=team.id,
            provider="cfbd",
            alias_name="UConn",
            normalized_alias="uconn",
            confidence=1.0,
            review_state="provider_asserted",
        )
    )
    db.commit()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="41",
        provider_name="Connecticut",
        provider_aliases=("UConn",),
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.team.id == team.id
    assert result.method == "exact_alias"


def test_database_alias_uniqueness_constraint_remains_enforced(db):
    team = Team(name="Alabama Crimson Tide", league="NCAAF", sport="NCAAF")
    db.add(team)
    db.flush()
    values = {
        "team_id": team.id,
        "provider": "cfbd",
        "alias_name": "Alabama",
        "normalized_alias": "alabama",
        "confidence": 1.0,
        "review_state": "provider_asserted",
    }
    db.add_all([TeamAlias(**values), TeamAlias(**values)])

    with pytest.raises(IntegrityError):
        db.flush()


REVIEWED_PROVIDER_CASES = [
    ("12", "Arizona", ("Arizona State Sun Devils",)),
    ("8", "Arkansas", ("Arkansas Pine Bluff Golden Lions", "Arkansas State Red Wolves")),
    ("38", "Colorado", ("Colorado State Rams",)),
    ("57", "Florida", ("Florida International Panthers", "Florida Atlantic Owls", "Florida State Seminoles", "Florida A&M Rattlers")),
    ("61", "Georgia", ("Georgia Southern Eagles", "Georgia Tech Yellow Jackets", "Georgia State Panthers")),
    ("248", "Houston", ("Houston Baptist Huskies",)),
    ("70", "Idaho", ("Idaho State Bengals",)),
    ("84", "Indiana", ("Indiana State Sycamores",)),
    ("2305", "Kansas", ("Kansas State Wildcats",)),
    ("309", "Louisiana", ("Louisiana Tech Bulldogs",)),
    ("2390", "Miami", ("Miami (OH) RedHawks",)),
    ("130", "Michigan", ("Michigan State Spartans",)),
    ("142", "Missouri", ("Missouri State Bears",)),
    ("167", "New Mexico", ("New Mexico State Aggies",)),
    ("153", "North Carolina", ("North Carolina A&T Aggies",)),
    ("77", "Northwestern", ("Northwestern State Demons",)),
    ("201", "Oklahoma", ("Oklahoma State Cowboys",)),
    ("2483", "Oregon", ("Oregon State Beavers",)),
    ("2633", "Tennessee", ("Tennessee State Tigers",)),
    ("251", "Texas", ("Texas State Bobcats", "Texas Tech Red Raiders", "Texas A&M Aggies")),
    ("258", "Virginia", ("Virginia Tech Hokies",)),
    ("264", "Washington", ("Washington State Cougars",)),
]


@pytest.mark.parametrize(
    ("provider_team_id", "provider_name", "neighbor_names"),
    REVIEWED_PROVIDER_CASES,
)
def test_reviewed_provider_mapping_resolves_only_intended_team(
    db,
    provider_team_id,
    provider_name,
    neighbor_names,
):
    canonical_name = REVIEWED_CFBD_TEAM_MAPPINGS[provider_team_id]
    intended = Team(name=canonical_name, league="NCAAF", sport="NCAAF")
    neighbors = [
        Team(name=name, league="NCAAF", sport="NCAAF") for name in neighbor_names
    ]
    db.add_all([intended, *neighbors])
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id=provider_team_id,
        provider_name=provider_name,
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.team.id == intended.id
    assert result.team.id not in {team.id for team in neighbors}
    assert result.method == "reviewed_provider_mapping"


def test_reviewed_provider_mapping_does_not_fall_back_when_target_is_missing(db):
    db.add(Team(name="Oregon State Beavers", league="NCAAF", sport="NCAAF"))
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="2483",
        provider_name="Oregon",
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.team is None
    assert result.method == "unresolved"


def test_directional_only_school_does_not_match_another_institution(db):
    southern_mississippi = Team(
        name="Southern Mississippi Golden Eagles",
        league="NCAAF",
        sport="NCAAF",
    )
    db.add(southern_mississippi)
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="2582",
        provider_name="Southern",
        sport="NCAAF",
        league="NCAAF",
    )

    assert result.method == "new_team"
    assert result.team.name == "Southern"
    assert result.team.id != southern_mississippi.id


def test_bootstrap_candidates_are_stable_when_new_teams_are_staged(db):
    south_carolina = Team(
        name="South Carolina Gamecocks",
        league="NCAAF",
        sport="NCAAF",
    )
    db.add(south_carolina)
    db.flush()
    candidate_team_ids = {south_carolina.id}
    db.add(Team(name="South Carolina State Bulldogs", league="NCAAF", sport="NCAAF"))
    db.flush()

    result = TeamIdentityService(db).resolve(
        provider="cfbd",
        provider_team_id="2579",
        provider_name="South Carolina",
        sport="NCAAF",
        league="NCAAF",
        candidate_team_ids=candidate_team_ids,
    )

    assert result.team.id == south_carolina.id
    assert result.method == "mascot_suffix"