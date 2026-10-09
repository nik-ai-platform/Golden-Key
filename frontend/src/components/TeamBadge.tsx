import { Box } from "@mui/material";

import { getTeamIdentity } from "../utils/teamIdentity";

export function TeamBadge({ sport, team }: { sport: string; team: string }) {
  const identity = getTeamIdentity(sport, team);
  const abbreviation = identity.abbreviation === "—"
    ? team.trim().split(/\s+/).map((word) => word[0]).join("").slice(0, 4).toUpperCase()
    : identity.abbreviation;
  return (
    <Box aria-hidden="true" data-testid="team-abbreviation-badge" sx={{
      width: 38, minHeight: 30, flexShrink: 0, display: "grid", placeItems: "center",
      color: "primary.main", border: "1px solid var(--gk-border-strong)", borderRadius: 1,
      backgroundColor: "var(--gk-surface-soft)", fontFamily: "var(--gk-font-mono)", fontSize: "0.68rem", fontWeight: 700,
    }}>
      {abbreviation}
    </Box>
  );
}
