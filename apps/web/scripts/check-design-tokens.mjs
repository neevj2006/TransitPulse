import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

const sourceRoot = path.resolve("src");
const violations = [];
const metadataColorFiles = new Set(["icon.tsx", "layout.tsx", "manifest.ts"]);

async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await inspect(target);
    } else if (/\.(tsx?|jsx?)$/.test(entry.name)) {
      const source = await readFile(target, "utf8");
      if (
        /#[0-9a-f]{3,8}\b/i.test(source) &&
        !target.endsWith("route-badge.tsx") &&
        !metadataColorFiles.has(entry.name)
      )
        violations.push(target);
    }
  }
}

await inspect(sourceRoot);

if (violations.length > 0) {
  throw new Error(
    `Use semantic design tokens instead of one-off colors:\n${violations.join("\n")}`,
  );
}
