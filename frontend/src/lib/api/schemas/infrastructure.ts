import { z } from "zod";

export const StandardResponseSchema = z.object({
  correlation_id: z.string(),
  data: z.unknown(),
});

export const VersionedTelemetryEnvelopeSchema = z.object({
  schema_version: z.number().default(1),
  generated_at: z.string(),
  _meta: z.object({
    collector_version: z.number(),
    generated_at: z.string(),
  }).optional().nullable(),
  data: z.unknown(),
});

export const HealthStatusSchema = z.enum(["ONLINE", "DELAYED", "DEGRADED", "OFFLINE", "UNKNOWN", "ERROR"]);

export const HistorySampleSchema = z.object({
  timestamp: z.string(),
  status: HealthStatusSchema,
  latency_ms: z.number(),
});

export const ServiceStateSchema = z.object({
  service: z.string(),
  status: HealthStatusSchema,
  available: z.boolean().optional().default(true),
  status_reason: z.string().nullable().optional(),
  latency_ms: z.number(),
  last_checked: z.string(),
  last_success: z.string().nullable().optional(),
  heartbeat_age_ms: z.number().nullable().optional(),
  ttl_remaining: z.number().nullable().optional(),
  collector_version: z.number().optional().default(1),
  metrics: z.record(z.string(), z.any()).optional().default({}),
  error: z.string().nullable().optional(),
});

export const ServiceContainerSchema = z.object({
  snapshot: ServiceStateSchema,
  history: z.array(HistorySampleSchema).optional().default([]),
});

export const InfrastructurePayloadSchema = z.object({
  health_score: z.object({
    score: z.number(),
    grade: z.string(),
    calculated_at: z.string().optional().nullable(),
  }),
  services: z.record(z.string(), ServiceContainerSchema),
});
