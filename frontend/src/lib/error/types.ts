export interface ErrorContext {
  route: string;
  userId: string | null;
  anonymousId: string | null;
  buildVersion: string;
  featureFlags: string[];
  browser: string;
  viewport: string;
  sessionId: string | null;
  [key: string]: any;
}

export interface ErrorAdapter {
  captureException(error: Error, context: Partial<ErrorContext>): void;
  captureMessage(message: string, context: Partial<ErrorContext>): void;
  captureWarning(message: string, context: Partial<ErrorContext>): void;
}
