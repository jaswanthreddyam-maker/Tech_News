import { ErrorAdapter, ErrorContext } from "../types";

export class CustomBackendAdapter implements ErrorAdapter {
  private endpoint = "/api/v1/telemetry/errors";

  private async sendPayload(level: string, message: string, stack: string | null, context: Partial<ErrorContext>) {
    try {
      await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, message, stack, context, timestamp: new Date().toISOString() }),
        keepalive: true
      });
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (e) {
      // Silently fail if backend is unreachable to avoid error loops
    }
  }

  captureException(error: Error, context: Partial<ErrorContext>) {
    this.sendPayload("error", error.message, error.stack || null, context);
  }
  
  captureMessage(message: string, context: Partial<ErrorContext>) {
    this.sendPayload("info", message, null, context);
  }

  captureWarning(message: string, context: Partial<ErrorContext>) {
    this.sendPayload("warning", message, null, context);
  }
}
