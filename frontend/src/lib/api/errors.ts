export class ApiError extends Error {
  status: number;
  code: string;
  correlationId?: string;

  constructor(message: string, status: number, code: string = "API_ERROR", correlationId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

export class ValidationError extends Error {
  errors: any[];

  constructor(message: string, errors: any[]) {
    super(message);
    this.name = "ValidationError";
    this.errors = errors;
  }
}

export class NotFoundError extends ApiError {
  constructor(message: string = "Resource not found", correlationId?: string) {
    super(message, 404, "NOT_FOUND", correlationId);
    this.name = "NotFoundError";
  }
}

export class AuthenticationError extends ApiError {
  constructor(message: string = "Authentication required", correlationId?: string) {
    super(message, 401, "UNAUTHORIZED", correlationId);
    this.name = "AuthenticationError";
  }
}

export class NetworkError extends Error {
  constructor(message: string = "Network connection failed") {
    super(message);
    this.name = "NetworkError";
  }
}

export class TimeoutError extends Error {
  constructor(message: string = "Request timed out") {
    super(message);
    this.name = "TimeoutError";
  }
}
