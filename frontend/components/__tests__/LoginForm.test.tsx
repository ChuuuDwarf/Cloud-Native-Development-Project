import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Stub the auth API so the AuthProvider's initial /me probe doesn't try to
// hit the network. We return a 401-shaped rejection so the provider settles
// into the "not authenticated" state.
const meMock = vi.fn().mockRejectedValue({ response: { status: 401 } });
const loginMock = vi.fn();
vi.mock("@/services/auth-api", () => ({
  authApi: {
    me: (...a: unknown[]) => meMock(...a),
    login: (...a: unknown[]) => loginMock(...a),
    logout: vi.fn(),
  },
}));

import { AuthProvider } from "@/contexts/AuthContext";
import { LoginForm } from "@/components/LoginForm";

describe("LoginForm", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("renders the email and password inputs and a submit button", () => {
    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    expect(
      screen.getByPlaceholderText("admin@example.com"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/密碼/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /登入/ })).toBeInTheDocument();
  });

  it("submitting calls authApi.login with the typed credentials and fires onSuccess", async () => {
    loginMock.mockResolvedValue({
      userId: "u-1",
      name: "A",
      email: "a@b.c",
      role: "system_admin",
      permissions: ["*"],
    });
    // After login, AuthProvider calls refresh() -> me(); make it resolve so the
    // re-render doesn't crash.
    meMock.mockResolvedValueOnce({
      id: "u-1",
      name: "A",
      email: "a@b.c",
      role: "system_admin",
      permissions: ["*"],
      labId: null,
      departmentId: null,
    });

    const onSuccess = vi.fn();
    render(
      <AuthProvider>
        <LoginForm onSuccess={onSuccess} />
      </AuthProvider>,
    );

    fireEvent.change(screen.getByPlaceholderText("admin@example.com"), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/密碼/), {
      target: { value: "Password1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /登入/ }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: "a@b.c",
        password: "Password1",
      });
    });
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("shows the AuthContext error message when login rejects", async () => {
    loginMock.mockRejectedValueOnce({
      response: { data: { error: { message: "bad creds" } } },
    });

    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    fireEvent.change(screen.getByPlaceholderText("admin@example.com"), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/密碼/), {
      target: { value: "Password1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /登入/ }));

    await waitFor(() => {
      expect(screen.getByText("bad creds")).toBeInTheDocument();
    });
  });
});
