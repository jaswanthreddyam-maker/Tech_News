import { migrateToV1 } from "./versions/v1";
import { migrateToV2 } from "./versions/v2";

const migrations = [
  { version: 1, up: migrateToV1 },
  { version: 2, up: migrateToV2 },
];

export const CURRENT_SCHEMA_VERSION = 2;

/**
 * Loads personalization state from localStorage and applies any pending migrations.
 */
export function loadAndMigrateStorage(key: string, defaultState: any): any {
  if (typeof window === "undefined") return defaultState;

  const stored = localStorage.getItem(key);
  if (!stored) {
    // Check for legacy v0 config before returning default
    const legacyState = migrateToV1(null, defaultState);
    if (legacyState.schemaVersion === 1) {
      // Legacy data found and migrated to v1.
      // Now run the remaining migrations if there are any.
      return runMigrations(legacyState, 1, defaultState);
    }
    return defaultState;
  }

  try {
    const parsed = JSON.parse(stored);
    const currentVersion = parsed.schemaVersion || 1;
    return runMigrations(parsed, currentVersion, defaultState);
  } catch (e) {
    // eslint-disable-next-line no-console

    return defaultState;
  }
}

function runMigrations(state: any, fromVersion: number, defaultState: any): any {
  let migratedState = { ...state };
  
  for (const migration of migrations) {
    if (migration.version > fromVersion) {
      // eslint-disable-next-line no-console

      migratedState = migration.up(migratedState, defaultState);
    }
  }

  migratedState.schemaVersion = CURRENT_SCHEMA_VERSION;
  return migratedState;
}
