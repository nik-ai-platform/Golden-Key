import { describe, expect, it } from "vitest";

import { NEUTRAL_TEAM_IDENTITY } from "../../src/data/teamIdentity";
import type { Prediction } from "../../src/types/product";
import {
  getPredictionTeam,
  getPredictionTeamIdentity,
  getTeamIdentity,
  hexToRgbChannels,
} from "../../src/utils/teamIdentity";

function prediction(overrides: Partial<Prediction> = {}): Prediction {
  return {
    prediction_id: 1,
    game_id: 1,
    sport: "NFL",
    home_team: "Buffalo Bills",
    away_team: "Miami Dolphins",
    game_date: "2026-09-03T00:00:00Z",
    market: "spread",
    selection: "HOME",
    display_selection: "Buffalo Bills -3.5",
    line_value: -3.5,
    american_odds: -110,
    sportsbook: null,
    odds_observed_at: null,
    model_version: "NPI-4.0",
    npi_score: 188,
    confidence_score: 82,
    simulation_probability: 71.8,
    projected_edge: 8.7,
    risk_level: "LOW",
    reasoning: null,
    ...overrides,
  };
}

describe("team identity", () => {
  it("resolves canonical teams without case or whitespace sensitivity", () => {
    expect(getTeamIdentity(" nfl ", "  buffalo   bills ")).toEqual({
      primary: "#00338D",
      secondary: "#C60C30",
      abbreviation: "BUF",
    });
  });

  it("resolves explicit college aliases", () => {
    expect(getTeamIdentity("NCAAF", "Georgia Bulldogs").abbreviation).toBe("UGA");
    expect(getTeamIdentity("NCAAB", "UConn Huskies").abbreviation).toBe("UCONN");
  });

  it("returns the neutral identity for an unknown team", () => {
    expect(getTeamIdentity("NCAAB", "Unknown College")).toBe(NEUTRAL_TEAM_IDENTITY);
  });

  it("resolves only side-based selections", () => {
    const homePick = prediction();
    const awayPick = prediction({ selection: "AWAY" });
    const namedPick = prediction({ selection: "Miami Dolphins +4.5" });
    const totalPick = prediction({ selection: "OVER", market: "total" });

    expect(getPredictionTeam(homePick)).toBe("Buffalo Bills");
    expect(getPredictionTeam(awayPick)).toBe("Miami Dolphins");
    expect(getPredictionTeam(namedPick)).toBe("Miami Dolphins");
    expect(getPredictionTeam(totalPick)).toBeNull();
    expect(getPredictionTeamIdentity(totalPick)).toBe(NEUTRAL_TEAM_IDENTITY);
  });

  it("converts identity colors to CSS RGB channels", () => {
    expect(hexToRgbChannels("#00338D")).toBe("0, 51, 141");
  });
});