import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TransferRiskCalculator } from "@/components/transfer-risk-calculator";

vi.mock("@/lib/api", () => ({
  apiRequest: vi.fn().mockResolvedValue({
    data: { sufficient_data: true, missed_transfer_probability: 0.25, risk_band: "MEDIUM", planned_buffer_seconds: 300, walking_seconds: 180, walking_time_source: "user", sample_size: 24, arrival_sample_size: 24, departure_sample_size: 24, source_first_at: "2026-07-01T00:00:00Z", source_last_at: "2026-08-01T00:00:00Z", history_stale: false, assumptions: ["Historical delays are independent."] },
    meta: { calculation_version: "2026-08-03.1" },
  }),
}));

describe("TransferRiskCalculator", () => {
  it("shows a plainly labelled empirical risk result", async () => {
    render(<QueryClientProvider client={new QueryClient()}><TransferRiskCalculator /></QueryClientProvider>);
    fireEvent.change(screen.getByLabelText("Planned connecting departure"), { target: { value: "2026-08-05T10:10" } });
    fireEvent.click(screen.getByRole("button", { name: "Calculate transfer risk" }));
    expect(await screen.findByText(/Medium risk/)).toBeInTheDocument();
    expect(screen.getByText(/not a guarantee/)).toBeInTheDocument();
  });
});
