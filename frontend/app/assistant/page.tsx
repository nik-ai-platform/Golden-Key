import React from "react";
import { Stack } from "@mui/material";

import { ChatWindow } from "../../components/assistant/ChatWindow";
import { ContextPanel } from "../../components/assistant/ContextPanel";
import { ConfidenceDisplay } from "../../components/assistant/ConfidenceDisplay";
import { SuggestionButtons } from "../../components/assistant/SuggestionButtons";

export default function AssistantPage() {
  return (
    <Stack spacing={2}>
      <ConfidenceDisplay value={82} />
      <SuggestionButtons />
      <ContextPanel />
      <ChatWindow />
    </Stack>
  );
}
