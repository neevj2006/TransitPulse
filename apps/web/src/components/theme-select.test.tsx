import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeSelect } from "./theme-select";

const setTheme = vi.fn();

vi.mock("next-themes", () => ({
  useTheme: () => ({ setTheme, theme: "system" }),
}));

describe("ThemeSelect", () => {
  beforeEach(() => setTheme.mockClear());

  it("offers system, light, and dark preferences", async () => {
    const user = userEvent.setup();
    render(<ThemeSelect />);

    const select = await screen.findByRole("combobox", { name: "Color theme" });
    expect(select).toBeEnabled();
    await user.selectOptions(select, "dark");
    expect(setTheme).toHaveBeenCalledWith("dark");
  });
});
