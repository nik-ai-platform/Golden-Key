from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TeamLocation = Literal["HOME", "AWAY"]
RuleSemantics = Literal["COVERS", "DOES_NOT_COVER"]


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    code: str
    team_location: TeamLocation
    spread: float
    semantics: RuleSemantics

    @property
    def pick_side(self) -> TeamLocation:
        if self.semantics == "COVERS":
            return self.team_location
        return "AWAY" if self.team_location == "HOME" else "HOME"


NCAAF_ATS_RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition("AWAY_NEG_4_5_COVERS", "AWAY", -4.5, "COVERS"),
    RuleDefinition("AWAY_NEG_7_5_COVERS", "AWAY", -7.5, "COVERS"),
    RuleDefinition("HOME_NEG_6_5_COVERS", "HOME", -6.5, "COVERS"),
    RuleDefinition("HOME_NEG_7_DOES_NOT_COVER", "HOME", -7.0, "DOES_NOT_COVER"),
    RuleDefinition("AWAY_NEG_3_5_DOES_NOT_COVER", "AWAY", -3.5, "DOES_NOT_COVER"),
    RuleDefinition("AWAY_NEG_4_DOES_NOT_COVER", "AWAY", -4.0, "DOES_NOT_COVER"),
    RuleDefinition("HOME_NEG_1_5_DOES_NOT_COVER", "HOME", -1.5, "DOES_NOT_COVER"),
    RuleDefinition("AWAY_NEG_2_5_COVERS", "AWAY", -2.5, "COVERS"),
    RuleDefinition("HOME_NEG_9_5_COVERS", "HOME", -9.5, "COVERS"),
    RuleDefinition("HOME_NEG_10_DOES_NOT_COVER", "HOME", -10.0, "DOES_NOT_COVER"),
    RuleDefinition("AWAY_NEG_5_COVERS", "AWAY", -5.0, "COVERS"),
    RuleDefinition("HOME_NEG_5_DOES_NOT_COVER", "HOME", -5.0, "DOES_NOT_COVER"),
    RuleDefinition("HOME_POS_13_COVERS", "HOME", 13.0, "COVERS"),
    RuleDefinition("HOME_NEG_5_5_DOES_NOT_COVER", "HOME", -5.5, "DOES_NOT_COVER"),
    RuleDefinition("HOME_NEG_6_DOES_NOT_COVER", "HOME", -6.0, "DOES_NOT_COVER"),
    RuleDefinition("AWAY_NEG_5_5_COVERS", "AWAY", -5.5, "COVERS"),
    RuleDefinition("HOME_NEG_7_5_DOES_NOT_COVER", "HOME", -7.5, "DOES_NOT_COVER"),
    RuleDefinition("HOME_NEG_4_5_COVERS", "HOME", -4.5, "COVERS"),
)


def match_ncaaf_ats_rule(
    spread_home: float | None,
    spread_away: float | None,
) -> RuleDefinition | None:
    matches = [
        rule
        for rule in NCAAF_ATS_RULES
        if (
            rule.team_location == "HOME"
            and spread_home is not None
            and spread_home == rule.spread
        )
        or (
            rule.team_location == "AWAY"
            and spread_away is not None
            and spread_away == rule.spread
        )
    ]
    if len(matches) > 1:
        codes = ", ".join(rule.code for rule in matches)
        raise ValueError(f"Multiple NCAAF ATS rules matched: {codes}")
    return matches[0] if matches else None