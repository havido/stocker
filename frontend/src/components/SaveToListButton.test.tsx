import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const apiPost = vi.fn();
const navigate = vi.fn();
const toastSuccess = vi.fn();
const toastError = vi.fn();
let authed = true;

vi.mock("@/lib/api", () => ({ apiPost: (...a: unknown[]) => apiPost(...a) }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ isAuthenticated: authed }) }));
vi.mock("react-router-dom", () => ({ useNavigate: () => navigate }));
vi.mock("sonner", () => ({
  toast: {
    success: (...a: unknown[]) => toastSuccess(...a),
    error: (...a: unknown[]) => toastError(...a),
  },
}));

import { SaveToListButton } from "@/components/SaveToListButton";

describe("SaveToListButton", () => {
  beforeEach(() => {
    apiPost.mockReset();
    navigate.mockReset();
    toastSuccess.mockReset();
    toastError.mockReset();
    authed = true;
  });

  it("saves the ticker to the watchlist when authenticated", async () => {
    apiPost.mockResolvedValue({ ticker: "AAPL", status: "added" });
    render(<SaveToListButton ticker="AAPL" />);

    fireEvent.click(screen.getByRole("button", { name: /save to list/i }));

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith("/v1/users/watchlist", { ticker: "AAPL" })
    );
    await waitFor(() => expect(screen.getByText(/saved to list/i)).toBeInTheDocument());
    expect(toastSuccess).toHaveBeenCalled();
  });

  it("prompts login (no save) when not authenticated", () => {
    authed = false;
    render(<SaveToListButton ticker="AAPL" />);

    fireEvent.click(screen.getByRole("button", { name: /save to list/i }));

    expect(apiPost).not.toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/login");
    expect(toastError).toHaveBeenCalled();
  });

  it("surfaces an error toast if the save fails", async () => {
    apiPost.mockRejectedValue(new Error("Failed to add ticker"));
    render(<SaveToListButton ticker="AAPL" />);

    fireEvent.click(screen.getByRole("button", { name: /save to list/i }));

    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Failed to add ticker"));
    expect(screen.queryByText(/saved to list/i)).not.toBeInTheDocument();
  });
});
