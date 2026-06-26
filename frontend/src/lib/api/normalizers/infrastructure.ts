import { apiClient } from "../client";
import { InfrastructurePayloadSchema } from "../schemas/infrastructure";
import { StandardResponseSchema } from "../schemas/common";
import { z } from "zod";

// The infrastructure endpoint returns:
// StandardResponse -> VersionedTelemetryEnvelope -> InfrastructurePayload
const InfrastructureEnvelopeSchema = z.object({
  schema_version: z.number().default(2),
  generated_at: z.string(),
  data: InfrastructurePayloadSchema,
});

const FullInfrastructureResponseSchema = StandardResponseSchema(InfrastructureEnvelopeSchema);

export async function fetchInfrastructureHealth() {
  const payload = await apiClient.fetchJson<unknown>("/admin/infrastructure");
  
  // Zod Validates the WRAPPER, the ENVELOPE, and the DATA all at once!
  const result = FullInfrastructureResponseSchema.safeParse(payload);
  
  if (!result.success) {

    throw new Error("Invalid infrastructure payload structure.");
  }
  
  return result.data.data.data; // StandardResponse.data -> Envelope.data
}
