import { Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";

import { sendAssistantMessage } from "../../src/services/assistantService";

export function ChatWindow() {
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("Golden Key AI is ready to explain picks, review your portfolio, and help build strategy.");
  const [route, setRoute] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isSending, setIsSending] = useState(false);

  async function handleSend() {
    if (!message.trim()) {
      return;
    }

    setIsSending(true);
    try {
      const response = await sendAssistantMessage(message);
      setAnswer(response.answer);
      setRoute(response.route ?? null);
      setConversationId(response.conversation_id ?? null);
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "The assistant service is unavailable.";
      setAnswer(messageText);
      setRoute(null);
      setConversationId(null);
    } finally {
      setIsSending(false);
      setMessage("");
    }
  }

  return (
    <Card sx={{ maxWidth: 720, mx: "auto" }}>
      <CardContent>
        <Typography variant="h5" gutterBottom>Golden Key AI</Typography>
        <Typography color="text.secondary" gutterBottom>Ask me anything about picks, portfolio, live games, or strategy.</Typography>
        <Stack spacing={2}>
          <Box sx={{ p: 2, borderRadius: 2, backgroundColor: "#f8fafc", border: "1px solid #e2e8f0" }}>
            <Typography variant="body1">{answer}</Typography>
            {route && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                Route: {route}
              </Typography>
            )}
            {conversationId && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                Conversation: #{conversationId}
              </Typography>
            )}
          </Box>
          <TextField
            label="Ask a question"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Why is this pick rated highly?"
          />
          <Button variant="contained" onClick={handleSend} disabled={isSending}>
            {isSending ? "Sending..." : "Send"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
