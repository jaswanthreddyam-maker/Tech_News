import { execSync } from 'child_process';
import { TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, TEST_ADMIN_ROLE } from './constants';

async function waitForBackend(url: string, timeoutMs: number = 30000) {
  const start = Date.now();
  console.log(`Waiting for backend health check at ${url}...`);
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        console.log("Backend is healthy!");
        return;
      }
    } catch (e) {
      // Ignore network errors during boot
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error(`Backend at ${url} did not become healthy within ${timeoutMs}ms.`);
}

async function globalSetup() {
  // 1. Perform health check smoke test before starting tests
  await waitForBackend('http://localhost:8000/api/v1/health/live');

  // 2. Create the test admin user
  console.log("Creating test admin user...");
  try {
    execSync(`docker compose exec -T backend python scripts/manage_test_user.py create ${TEST_ADMIN_EMAIL} ${TEST_ADMIN_PASSWORD} ${TEST_ADMIN_ROLE}`, {
      stdio: 'inherit'
    });
  } catch (err: any) {
    console.warn("Failed to create test admin user via Docker Compose. Retrying locally...", err.message);
    // Fallback if docker is not used or exec fails (e.g. local host development environment)
    const pythonExec = process.platform === 'win32' ? '.\\\\venv\\\\Scripts\\\\python.exe' : './venv/bin/python';
    execSync(`${pythonExec} scripts/manage_test_user.py create ${TEST_ADMIN_EMAIL} ${TEST_ADMIN_PASSWORD} ${TEST_ADMIN_ROLE}`, {
      stdio: 'inherit',
      cwd: '../backend'
    });
  }
}

export default globalSetup;
