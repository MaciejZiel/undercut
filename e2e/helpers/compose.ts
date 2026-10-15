import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { REPO_ROOT } from "./config";

const run = promisify(execFile);

/** Runs `docker compose <args>` in the repository root and returns stdout. */
export async function compose(args: string[], timeoutMs = 120_000): Promise<string> {
  const { stdout } = await run("docker", ["compose", ...args], {
    cwd: REPO_ROOT,
    timeout: timeoutMs,
    maxBuffer: 64 * 1024 * 1024,
  });
  return stdout;
}

/** Runs a Django management command inside the backend container. */
export function manage(args: string[], timeoutMs = 120_000): Promise<string> {
  return compose(["exec", "-T", "backend", "python", "manage.py", ...args], timeoutMs);
}

export type SeededRound = { year: number; round: number; qualifying_start: string; locked: boolean };

/** (Re)opens the prediction round, or closes it with `--lock`. The last output line is JSON. */
export async function seedRound(options: { lock?: boolean } = {}): Promise<SeededRound> {
  const out = await manage(["seed_e2e", ...(options.lock ? ["--lock"] : [])]);
  const last = out.trim().split("\n").at(-1) ?? "";
  return JSON.parse(last) as SeededRound;
}
