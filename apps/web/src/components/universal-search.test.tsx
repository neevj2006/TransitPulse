import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UniversalSearch } from "@/components/universal-search";

describe("UniversalSearch", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: [
              {
                kind: "route",
                id: "Red",
                label: "Red Line",
                detail: "Rapid transit",
                route_color: ["#", "DA291C"].join(""),
              },
            ],
          }),
          { status: 200 },
        ),
      ),
    );
  });
  it("announces and groups scheduled search results", async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <UniversalSearch />
      </QueryClientProvider>,
    );
    await user.type(screen.getByRole("combobox"), "red");
    expect(
      await screen.findByRole("link", { name: /Red Line/ }),
    ).toHaveAttribute("href", "/routes/Red");
    expect(screen.getByText("routes")).toBeInTheDocument();
  });
});
