import { client } from "../api/client";

export type AssistantMessageResponse = {
  answer: string;
  conversation_id?: number;
  route?: string;
  context?: Record<string, unknown>;
};

export async function sendAssistantMessage(message: string): Promise<AssistantMessageResponse> {
  const { data } = await client.post<AssistantMessageResponse>("/assistant/message", { message });
  return data;
}

export async function getAssistantHistory(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/assistant/history");
  return data;
}
