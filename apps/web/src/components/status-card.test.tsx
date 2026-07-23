import { render, screen } from "@testing-library/react";
import { CircleCheck } from "lucide-react";
import { describe, expect, it } from "vitest";
import { StatusCard } from "./status-card";

describe("StatusCard", () => {
  it("communicates status with visible text", () => {
    render(
      <StatusCard
        description="The interface rendered."
        icon={CircleCheck}
        label="Ready"
        tone="success"
        value="Web interface"
      />,
    );

    expect(screen.getByText("Ready")).toBeVisible();
    expect(screen.getByText("Web interface")).toBeVisible();
    expect(screen.getByText("The interface rendered.")).toBeVisible();
  });
});
