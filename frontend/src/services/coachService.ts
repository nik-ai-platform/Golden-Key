import { client } from "../api/client";

export type CoachChatResponse = {
  answer: string;
  warnings?: string[];
  context?: Record<string, unknown>;
  strategy?: Record<string, unknown>;
  learning?: Record<string, unknown>;
};

export type CoachBriefingResponse = {
  briefing?: {
    headline?: string;
    focus?: string[];
    profile?: Record<string, unknown>;
  };
  guidance?: string;
};

export async function askCoach(payload: { user_id?: number; question: string }): Promise<CoachChatResponse> {
  const { data } = await client.post<CoachChatResponse>("/coach/chat", payload);
  return data;
}

export async function getCoachBriefing(userId = 1): Promise<CoachBriefingResponse> {
  const { data } = await client.get<CoachBriefingResponse>(`/coach/briefing?user_id=${userId}`);
  return data;
}

export async function getCoachRecommendations(userId = 1): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>(`/coach/recommendations?user_id=${userId}`);
  return data;
}
