import { Button, Stack } from "@mui/material";

export function SuggestionButtons() {
  const suggestions = [
    "Analyze This Game",
    "Explain This Pick",
    "Compare Two Teams",
    "Build Strategy",
    "Review My Portfolio",
    "Find Value",
  ];

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {suggestions.map((item) => (
        <Button key={item} variant="outlined" size="small">
          {item}
        </Button>
      ))}
    </Stack>
  );
}
