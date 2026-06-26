// import * as Sentry from "@sentry/nextjs";
import { ErrorAdapter, ErrorContext } from "../types";

export class SentryAdapter implements ErrorAdapter {
  captureException(_error: Error, _context: Partial<ErrorContext>) {
    // Sentry.withScope((scope) => {
    //   scope.setExtras(context);
    //   Sentry.captureException(error);
    // });
  }
  
  captureMessage(_message: string, _context: Partial<ErrorContext>) {
    // Sentry.withScope((scope) => {
    //   scope.setExtras(context);
    //   Sentry.captureMessage(message, "info");
    // });
  }

  captureWarning(_message: string, _context: Partial<ErrorContext>) {
    // Sentry.withScope((scope) => {
    //   scope.setExtras(context);
    //   Sentry.captureMessage(message, "warning");
    // });
  }
}
