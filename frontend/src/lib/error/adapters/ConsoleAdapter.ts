import { ErrorAdapter, ErrorContext } from "../types";

export class ConsoleAdapter implements ErrorAdapter {
  captureException(error: Error, context: Partial<ErrorContext>) {
    // eslint-disable-next-line no-console

  }
  
  captureMessage(message: string, context: Partial<ErrorContext>) {
    // eslint-disable-next-line no-console
    console.info("[ConsoleAdapter] Message:", message, "\nContext:", context);
  }

  captureWarning(message: string, context: Partial<ErrorContext>) {
    // eslint-disable-next-line no-console

  }
}
