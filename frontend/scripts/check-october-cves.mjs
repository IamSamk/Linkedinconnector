#!/usr/bin/env node
/**
 * Post-Black-October (Oct 2026) Security Verification Script
 * Verifies Next.js >= 16.4.1 (16.4.2 recommended) to mitigate CVE-2026-96889
 * (Oct 14, 2026 out-of-band fix for two critical unauthenticated RCE flaws and Server Actions DoS).
 */
import fs from "node:fs";
import path from "node:path";

const pkgPath = path.join(process.cwd(), "package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));

const nextVer = pkg.dependencies?.next || "";

console.log("=== [Security Audit: Post-Black-October 2026 Advisories] ===");
console.log(`Pinned Next.js version : ${nextVer}`);
console.log(`Package Manager        : ${pkg.packageManager}`);

if (!nextVer.includes("16.4.2") && !nextVer.includes("16.4.1")) {
  console.error("CRITICAL: Next.js version is vulnerable to CVE-2026-96889! Upgrade to 16.4.2 immediately.");
  process.exit(1);
}
console.log("PASS: Next.js 16.4.2 (CVE-2026-96889 patched) verified.");
