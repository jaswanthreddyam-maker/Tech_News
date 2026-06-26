import { z } from "zod";

export function StandardResponseSchema<T>(dataSchema: z.ZodType<T>) {
  return z.object({
    status: z.enum(["success", "error"]),
    correlation_id: z.string().optional(),
    message: z.string().optional(),
    data: dataSchema,
  });
}

export function PaginatedResponseSchema<T>(dataSchema: z.ZodType<T>) {
  return z.object({
    status: z.enum(["success", "error"]),
    correlation_id: z.string().optional(),
    message: z.string().optional(),
    data: z.array(dataSchema),
    pagination: z.object({
      next_cursor: z.string().nullable().optional(),
      has_more: z.boolean(),
      limit: z.number(),
    }).optional(),
  });
}
