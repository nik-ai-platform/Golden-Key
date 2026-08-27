export type Game = {
  id: number;
  sport: string;
  league: string;
  home_team_id: number;
  away_team_id: number;
  game_date: string;
  home_score: number | null;
  away_score: number | null;
  winner_team_id: number | null;
};
