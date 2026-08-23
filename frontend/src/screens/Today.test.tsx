/**
 * Today screen behaviour: ordering, ticking, un-ticking, bonuses, and the
 * absence of any failure state on an unfinished day.
 */

import { waitFor, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as endpoints from "../api/endpoints";
import { completeInToday, bonusInToday } from "../api/optimistic";
import { habit, renderWithProviders, todayView } from "../test/utils";
import { Today } from "./Today";

vi.mock("../api/endpoints");

const mocked = vi.mocked(endpoints);

const SHOWER = habit({ id: 1, name: "Shower", sort_order: 1 });
const READING = habit({ id: 2, name: "Reading", sort_order: 2 });
const WATER = habit({ id: 3, name: "Water", sort_order: 3, anytime: true });
const LAUNDRY = habit({ id: 4, name: "Laundry", sort_order: 4 });

function board() {
  return todayView({
    active: [SHOWER, READING, WATER],
    available_extras: [LAUNDRY],
  });
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("rendering the day", () => {
  it("shows the habits in the order the API returned them", async () => {
    mocked.getToday.mockResolvedValue(board());

    renderWithProviders(<Today />);

    await screen.findByText("Shower");
    const names = screen.getAllByRole("button", { pressed: false });
    expect(names.map((node) => node.textContent)).toEqual([
      expect.stringContaining("Shower"),
      expect.stringContaining("Reading"),
      expect.stringContaining("Water"),
    ]);
  });

  it("shows the percentage and how many are left", async () => {
    mocked.getToday.mockResolvedValue(board());

    renderWithProviders(<Today />);

    expect(await screen.findByText("0%")).toBeInTheDocument();
    expect(screen.getByText("0 done · 3 to go")).toBeInTheDocument();
  });

  it("presents a rest day gently rather than as zero", async () => {
    mocked.getToday.mockResolvedValue(todayView({ active: [] }));

    renderWithProviders(<Today />);

    expect(await screen.findByText("A rest day")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("renders nothing that reads as a failure on an unfinished day", async () => {
    mocked.getToday.mockResolvedValue(board());

    const { container } = renderWithProviders(<Today />);
    await screen.findByText("Shower");

    expect(container.textContent).not.toMatch(/fail|missed|behind|overdue|streak/i);
  });
});

describe("ticking", () => {
  it("moves a habit to the completed pile", async () => {
    const user = userEvent.setup();
    const initial = board();
    mocked.getToday.mockResolvedValue(initial);
    mocked.complete.mockResolvedValue(completeInToday(initial, 1));

    renderWithProviders(<Today />);
    await user.click(await screen.findByText("Shower"));

    await waitFor(() => {
      expect(screen.getByRole("button", { pressed: true })).toHaveTextContent("Shower");
    });
    expect(mocked.complete).toHaveBeenCalledWith({ habit_id: 1, date: initial.date });
  });

  it("updates optimistically before the server answers", async () => {
    const user = userEvent.setup();
    const initial = board();
    mocked.getToday.mockResolvedValue(initial);
    // Never resolves during the assertion window.
    mocked.complete.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<Today />);
    await user.click(await screen.findByText("Shower"));

    await waitFor(() => expect(screen.getByText("33%")).toBeInTheDocument());
  });

  it("rolls back and explains when the tick fails", async () => {
    const user = userEvent.setup();
    const initial = board();
    mocked.getToday.mockResolvedValue(initial);
    mocked.complete.mockRejectedValue(
      Object.assign(new Error("nope"), { name: "ApiError" }),
    );

    renderWithProviders(<Today />);
    await user.click(await screen.findByText("Shower"));

    await waitFor(() => {
      expect(screen.getByText("0 done · 3 to go")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { pressed: true })).not.toBeInTheDocument();
  });

  it("un-ticks a completed habit back onto the active list", async () => {
    const user = userEvent.setup();
    const completed = completeInToday(board(), 1);
    mocked.getToday.mockResolvedValue(completed);
    mocked.uncomplete.mockResolvedValue(board());

    renderWithProviders(<Today />);
    const done = await screen.findByRole("button", { pressed: true });
    await user.click(done);

    await waitFor(() => {
      expect(screen.queryByRole("button", { pressed: true })).not.toBeInTheDocument();
    });
    expect(mocked.uncomplete).toHaveBeenCalled();
  });
});

describe("something extra", () => {
  it("logs a bonus that joins the pile without counting", async () => {
    const user = userEvent.setup();
    const initial = board();
    mocked.getToday.mockResolvedValue(initial);
    mocked.addBonus.mockResolvedValue(bonusInToday(initial, 4));

    renderWithProviders(<Today />);
    await user.click(await screen.findByRole("button", { name: /add something extra/i }));
    await user.click(await screen.findByText("Laundry"));

    await waitFor(() => {
      expect(screen.getByText(/bonus/)).toBeInTheDocument();
    });
    // The count and percentage are untouched by a bonus.
    expect(screen.getByText("0 done · 3 to go")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("says so plainly when there is nothing extra to add", async () => {
    const user = userEvent.setup();
    mocked.getToday.mockResolvedValue(todayView({ active: [SHOWER] }));

    renderWithProviders(<Today />);
    await user.click(await screen.findByRole("button", { name: /add something extra/i }));

    expect(
      await screen.findByText(/already scheduled today/i),
    ).toBeInTheDocument();
  });
});
