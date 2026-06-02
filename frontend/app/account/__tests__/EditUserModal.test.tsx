import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { UserResponse } from "@/types/user";

// Mock the API/services layer exactly like the existing AccountPage test does.
const updateMock = vi.fn();
vi.mock("@/services/user-api", () => ({
  userApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: (...args: unknown[]) => updateMock(...args),
    getById: vi.fn(),
  },
}));

import EditUserModal from "@/../app/account/EditUserModal";

const roles = [
  { id: "r-1", name: "system_admin" },
  { id: "r-2", name: "lab_supervisor" },
];
const labs = [{ id: "lab-1", code: "L01", name: "Lab 1" }];
const departments = [{ id: "dept-1", code: "D01", name: "Dept 1" }];

const baseUser: UserResponse = {
  id: "u-2",
  email: "supervisor@example.com",
  name: "Supervisor",
  phoneNumber: "0911111111",
  departmentId: null,
  labId: "lab-1",
  status: "active",
  isActive: true,
  roles: [{ id: "r-2", name: "lab_supervisor" }],
  createdAt: "2026-05-01T00:00:00Z",
  updatedAt: "2026-05-01T00:00:00Z",
};

function renderModal(
  overrides: Partial<{ user: UserResponse; onClose: () => void; onSaved: () => void }> = {}
) {
  const onClose = overrides.onClose ?? vi.fn();
  const onSaved = overrides.onSaved ?? vi.fn();
  const user = overrides.user ?? baseUser;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <EditUserModal
        user={user}
        roles={roles}
        labs={labs}
        departments={departments}
        onClose={onClose}
        onSaved={onSaved}
      />
    </QueryClientProvider>
  );
  return { onClose, onSaved };
}

describe("EditUserModal", () => {
  beforeEach(() => {
    updateMock.mockReset();
    updateMock.mockResolvedValue({ id: "u-2" });
  });

  it("renders the dialog reachable via getByRole('dialog') with the user's email", () => {
    renderModal();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("編輯使用者")).toBeInTheDocument();
    expect(screen.getByText("supervisor@example.com")).toBeInTheDocument();
  });

  it("calls onClose when the presentation backdrop is clicked", () => {
    const { onClose } = renderModal();
    const backdrop = screen.getByRole("dialog").parentElement as HTMLElement;
    expect(backdrop).toHaveAttribute("role", "presentation");
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onClose when clicking inside the dialog (stopPropagation)", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByText("編輯使用者"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onClose when Escape is pressed on the backdrop", () => {
    const { onClose } = renderModal();
    const backdrop = screen.getByRole("dialog").parentElement as HTMLElement;
    fireEvent.keyDown(backdrop, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does NOT close on a non-Escape key on the backdrop", () => {
    const { onClose } = renderModal();
    const backdrop = screen.getByRole("dialog").parentElement as HTMLElement;
    fireEvent.keyDown(backdrop, { key: "a" });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("strips non-digits and caps the phone input at 10 chars (replaceAll handler)", () => {
    renderModal();
    const phone = screen.getByPlaceholderText("例:0912345678") as HTMLInputElement;
    fireEvent.change(phone, { target: { value: "09 (87) 654-321-09999" } });
    expect(phone.value).toBe("0987654321");
  });

  it("submits only the changed fields and closes on success", async () => {
    const { onClose, onSaved } = renderModal();

    const phone = screen.getByPlaceholderText("例:0912345678");
    fireEvent.change(phone, { target: { value: "x0922222222y" } });

    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);

    await waitFor(() => expect(updateMock).toHaveBeenCalledTimes(1));
    const [userId, payload] = updateMock.mock.calls[0];
    expect(userId).toBe("u-2");
    expect(payload).toEqual({ phoneNumber: "0922222222" });
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("closes without calling the API when nothing changed", async () => {
    const { onClose } = renderModal();
    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(updateMock).not.toHaveBeenCalled();
  });

  it("rejects a phone that is not exactly 10 digits without calling the API", async () => {
    renderModal();
    fireEvent.change(screen.getByPlaceholderText("例:0912345678"), {
      target: { value: "123" },
    });
    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);
    expect(await screen.findByText("電話需為 10 位數字")).toBeInTheDocument();
    expect(updateMock).not.toHaveBeenCalled();
  });

  it("surfaces the API error message on a failed update", async () => {
    updateMock.mockRejectedValue({
      response: { data: { error: { message: "更新衝突" } } },
    });
    renderModal();
    fireEvent.change(screen.getByPlaceholderText("例:0912345678"), {
      target: { value: "0933333333" },
    });
    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);
    expect(await screen.findByText("更新衝突")).toBeInTheDocument();
  });

  it("calls onClose when the 取消 button is clicked", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByText("取消"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
