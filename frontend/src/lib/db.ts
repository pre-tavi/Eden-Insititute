/**
 * Neon Serverless Database Client Utility.
 * Uses safe environment resolution compatible with strict browser TypeScript (`tsc -b`)
 * and Node/SSR runtimes without requiring `@types/node` globals.
 */
import { neon } from "@neondatabase/serverless";

function resolveDatabaseUrl(): string {
  const metaEnv = (import.meta as unknown as { env?: Record<string, string | undefined> }).env;
  if (metaEnv?.VITE_DATABASE_URL) {
    return metaEnv.VITE_DATABASE_URL;
  }

  const nodeProcess = (
    globalThis as unknown as { process?: { env?: Record<string, string | undefined> } }
  ).process;

  return (
    nodeProcess?.env?.DATABASE_URL ||
    nodeProcess?.env?.POSTGRES_URL ||
    ""
  );
}

export function getNeonClient(explicitUrl?: string) {
  const connectionString = explicitUrl ?? resolveDatabaseUrl();
  if (!connectionString) {
    throw new Error("DATABASE_URL is not defined in environment variables.");
  }
  return neon(connectionString);
}