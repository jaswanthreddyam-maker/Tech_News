import { apiFetch } from "./client";

export interface BriefingLastDelivery {
  delivered_at: string;
  status: string;
  provider_message_id: string;
  stories_count: number;
}

export interface BriefingPreferences {
  email: string;
  email_verified: boolean;
  enabled: boolean;
  delivery_time: string;
  timezone: string;
  story_count: number;
  topics: string[];
  last_delivery?: BriefingLastDelivery | null;
}

export interface BriefingUpdateRequest {
  email: string;
  enabled: boolean;
  delivery_time: string;
  timezone: string;
  story_count: number;
  topics: string[];
}

export async function getBriefingPreferences(
  email: string = "jeshu@example.com"
): Promise<BriefingPreferences> {
  return apiFetch<BriefingPreferences>("/briefing/preferences", {
    params: { email },
  });
}

export async function updateBriefingPreferences(
  data: BriefingUpdateRequest
): Promise<{ status: string; message: string; preferences: BriefingPreferences }> {
  return apiFetch("/briefing/preferences", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function sendTestBriefing(email: string): Promise<{
  status: string;
  message: string;
  delivery_id: number;
  provider_message_id: string;
  stories_delivered: number;
}> {
  return apiFetch("/briefing/send-test", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function sendVerificationEmail(email: string): Promise<{
  status: string;
  message: string;
}> {
  return apiFetch("/briefing/verify-email", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}
