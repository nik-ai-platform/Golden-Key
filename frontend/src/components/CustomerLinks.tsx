import { Link, Stack } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

export function CustomerLinks() {
  return <Stack component="nav" aria-label="Customer information" direction="row" useFlexGap flexWrap="wrap" spacing={2} sx={{ mt: 2 }}>
    {[
      ["/", "Product"],
      ["/how-it-works", "Metric education"],
      ["/terms", "Terms"],
      ["/privacy", "Privacy"],
      ["/responsible-gaming", "Responsible gaming"],
      ["/disclaimer", "Disclaimer"],
      ["/support", "Support"],
    ].map(([path, label]) => <Link key={path} component={RouterLink} to={path} variant="body2">{label}</Link>)}
  </Stack>;
}
