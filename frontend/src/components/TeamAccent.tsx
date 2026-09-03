import { Box } from "@mui/material";

import type { TeamIdentity } from "../data/teamIdentity";
import { hexToRgbChannels } from "../utils/teamIdentity";

interface TeamAccentProps {
  identity: TeamIdentity;
  variant: "glow" | "dot" | "bar";
  testId?: string;
}

export function TeamAccent({ identity, variant, testId }: TeamAccentProps) {
  const primary = hexToRgbChannels(identity.primary);
  const secondary = identity.secondary ? hexToRgbChannels(identity.secondary) : primary;

  if (variant === "glow") {
    return (
      <Box
        aria-hidden="true"
        data-testid={testId}
        sx={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background: [
            `linear-gradient(110deg, rgba(${primary}, 0.11) 0%, rgba(${primary}, 0.035) 38%, transparent 68%)`,
            `radial-gradient(circle at 8% 10%, rgba(${secondary}, 0.04), transparent 30%)`,
          ].join(", "),
        }}
      />
    );
  }

  return (
    <Box
      aria-hidden="true"
      data-testid={testId}
      sx={{
        width: variant === "dot" ? 7 : 3,
        height: variant === "dot" ? 7 : 24,
        flexShrink: 0,
        backgroundColor: identity.primary,
        borderRadius: variant === "dot" ? "50%" : 0,
        boxShadow: variant === "dot" ? `0 0 8px rgba(${primary}, 0.3)` : "none",
      }}
    />
  );
}