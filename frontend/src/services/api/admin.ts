import { apiFetch } from "../api";
import type { components } from "./schema";

export type Notification = components["schemas"]["NotificationResponse"];
export type AIJob = components["schemas"]["AIJobHistoryResponse"];
export type CostAggregation = components["schemas"]["AI_CostAggregationResponse"];

export type NotificationList = components["schemas"]["NotificationListResponse"];

export async function getNotifications(): Promise<Notification[]> {
  const response = await apiFetch<NotificationList>("/admin/notifications");
  return response.notifications || [];
}

export async function getAiJobs(): Promise<AIJob[]> {
  const response = await apiFetch<AIJob[]>("/admin/ai/jobs");
  return response;
}

export async function getAiCosts(): Promise<CostAggregation> {
  const response = await apiFetch<CostAggregation>("/admin/ai/costs");
  return response;
}

export async function testAiPrompt(payload: { prompt_version: string, model: string, text: string }): Promise<any> {
  const response = await apiFetch<any>("/admin/ai/test", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return response;
}
