export type Team = {
  id: number;
  name: string;
  sport: string;
  league: string;
};

export type TeamIntelligence = {
  team_id: number;
  team_name: string;
  momentum: number;
  consistency: number;
  trend: string;
  home_win_pct: number;
  away_win_pct: number;
  average_margin: number;
  offensive_rating: number;
  defensive_rating: number;
  strength_rating: number;
};

export type TeamIntelligenceDetail = TeamIntelligence & {
  home_record?: string;
  away_record?: string;
};
