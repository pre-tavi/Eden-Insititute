/**
 * End-to-End Neon PostgreSQL Connectivity Verification Script.
 * - Forces IPv4-first DNS resolution on Linux/Parrot OS to prevent Node undici
 *   `internalConnectMultiple` dual-stack IPv6 ETIMEDOUT errors.
 * - Includes cold-start wake-up retries for Neon scale-to-zero compute nodes.
 */
import * as dns from "node:dns";
import * as fs from "node:fs";
import { createRequire } from "node:module";
import * as net from "node:net";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

// Fix Node.js undici dual-stack IPv6/IPv4 ETIMEDOUT on Linux
dns.setDefaultResultOrder("ipv4first");
if (typeof net.setDefaultAutoSelectFamily === "function") {
  net.setDefaultAutoSelectFamily(false);
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");

for (const envName of [".env", ".env.local"]) {
  const envPath = path.join(repoRoot, envName);
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, "utf8");
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      const eqIdx = line.indexOf("=");
      if (eqIdx === -1) continue;
      const key = line.slice(0, eqIdx).trim();
      let val = line.slice(eqIdx + 1).trim();
      if (
        (val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))
      ) {
        val = val.slice(1, -1);
      }
      process.env[key] = val;
    }
  }
}

const dbUrl =
  process.env.DATABASE_URL ||
  process.env.POSTGRES_URL ||
  process.env.DATABASE_URL_UNPOOLED;

if (!dbUrl || dbUrl.startsWith("sqlite:")) {
  console.error(
    "FAIL: No Neon PostgreSQL DATABASE_URL found in .env.local or .env."
  );
  process.exit(1);
}

const requireFromFrontend = createRequire(
  path.join(repoRoot, "frontend", "package.json")
);
const { neon } = requireFromFrontend("@neondatabase/serverless");

const sql = neon(dbUrl);
const maxAttempts = 3;

for (let attempt = 1; attempt <= maxAttempts; attempt++) {
  try {
    if (attempt > 1) {
      console.log(`Retrying Neon connection (attempt ${attempt}/${maxAttempts})...`);
    }
    const rows = await sql`
      SELECT
        NOW() AS current_time,
        current_database() AS db_name,
        current_user AS db_user,
        version() AS pg_version;
    `;
    console.log("==============================================================");
    console.log("SUCCESS: Connected to Neon Serverless PostgreSQL!");
    console.log("Database :", rows[0].db_name);
    console.log("User     :", rows[0].db_user);
    console.log("Timestamp:", rows[0].current_time);
    console.log("Version  :", rows[0].pg_version.split(",")[0]);
    console.log("==============================================================");
    process.exit(0);
  } catch (error) {
    if (attempt === maxAttempts) {
      console.error("FAIL: Neon PostgreSQL connection failed after retries:", error);
      process.exit(1);
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}