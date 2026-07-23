import { describe, expect, it } from "vitest";

describe("CI blocking proof", () => {
  it("deliberately fails before branch protection is enabled", () => {
    expect("blocked").toBe("passing");
  });
});
