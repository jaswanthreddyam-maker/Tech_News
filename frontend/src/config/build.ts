export const BUILD_CONFIG = {
  version: "1.0.0-rc1",
  commit: process.env.NEXT_PUBLIC_COMMIT_SHA || "unknown",
  buildDate: process.env.NEXT_PUBLIC_BUILD_DATE || new Date().toISOString(),
  environment: process.env.NODE_ENV || "development"
};
