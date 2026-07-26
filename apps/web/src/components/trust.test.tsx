import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataValue, SourceBadge, StatePanel } from "@/components/trust";

describe("trust components", () => {
  it("labels live values with a source instead of color alone", () => {
    render(<DataValue value="6 min" kind="live" detail="Agency prediction" />);
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("Agency prediction")).toBeInTheDocument();
  });
  it("explains scheduled fallback", () => {
    render(
      <StatePanel kind="fallback" title="Live unavailable">
        Showing schedule.
      </StatePanel>,
    );
    expect(screen.getByText("Live unavailable")).toBeInTheDocument();
    expect(screen.getByText("Showing schedule.")).toBeInTheDocument();
  });
  it("renders an explicit unknown badge", () => {
    render(<SourceBadge kind="unknown" />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });
});
