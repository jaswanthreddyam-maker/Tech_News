import { execSync } from 'child_process';
import { TEST_ADMIN_EMAIL } from './constants';

async function globalTeardown() {
  console.log("Cleaning up test admin user...");
  try {
    execSync(`docker compose exec -T backend python scripts/manage_test_user.py delete ${TEST_ADMIN_EMAIL}`, {
      stdio: 'inherit'
    });
  } catch (err: any) {
    console.warn("Failed to delete test admin user via Docker Compose. Retrying locally...", err.message);
    const pythonExec = process.platform === 'win32' ? '.\\\\venv\\\\Scripts\\\\python.exe' : './venv/bin/python';
    execSync(`${pythonExec} scripts/manage_test_user.py delete ${TEST_ADMIN_EMAIL}`, {
      stdio: 'inherit',
      cwd: '../backend'
    });
  }
}

export default globalTeardown;
