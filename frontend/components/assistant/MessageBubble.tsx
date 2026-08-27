import { Box, Typography } from "@mui/material";

export function MessageBubble({ text, role }: { text: string; role: "user" | "assistant" }) {
  return (
    <Box sx={{ alignSelf: role === "user" ? "flex-end" : "flex-start", backgroundColor: role === "user" ? "#0f766e" : "#f1f5f9", color: role === "user" ? "white" : "#0f172a", px: 2, py: 1, borderRadius: 999 }}>
      <Typography variant="body2">{text}</Typography>
    </Box>
  );
}
