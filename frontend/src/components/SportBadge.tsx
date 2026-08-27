import { Chip } from "@mui/material";

export function SportBadge({ sport }: { sport: string }) {
  return <Chip label={sport} size="small" variant="outlined" sx={{ fontWeight: 700, letterSpacing: 0.6 }} />;
}
