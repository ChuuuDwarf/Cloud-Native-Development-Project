import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock the API/services layer exactly like the existing AccountPage test does.
const createMock = vi.fn();
vi.mock("@/services/user-api", () => ({
  userApi: {
    list: vi.fn(),
    create: (...args: unknown[]) => createMock(...args),
    update: vi.fn(),
    getById: vi.fn(),
  },
}));

import CreateUserModal from "@/../app/account/CreateUserModal";

const roles = [
  { id: "r-1", name: "system_admin" },
  { id: "r-2", name: "lab_supervisor" },
];
const labs = [{ id: "lab-1", code: "L01", name: "Lab 1" }];
const departments = [{ id: "dept-1", code: "D01", name: "Dept 1" }];

function renderModal(overrides: Partial<{ onClose: () => void; onCreated: () => void }> = {}) {
  const onClose = overrides.onClose ?? vi.fn();
  const onCreated = overrides.onCreated ?? vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <CreateUserModal
        roles={roles}
        labs={labs}
        departments={departments}
        onClose={onClose}
        onCreated={onCreated}
      />
    </QueryClientProvider>
  );
  return { onClose, onCreated };
}

describe("CreateUserModal", () => {
  beforeEach(() => {
    createMock.mockReset();
    createMock.mockResolvedValue({ id: "u-new" });
  });

  it("renders the dialog reachable via getByRole('dialog')", () => {
    renderModal();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("建立使用者")).toBeInTheDocument();
  });

  it("calls onClose when the presentation backdrop is clicked", () => {
    const { onClose } = renderModal();
    const dialog = screen.getByRole("dialog");
    // The backdrop is the parent of the dialog (role="presentation").
    const backdrop = dialog.parentElement as HTMLElement;
    expect(backdrop).toHaveAttribute("role", "presentation");
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onClose when clicking inside the dialog (stopPropagation)", () => {
    const { onClose } = renderModal();
    // Heading lives inside the <form>, which stops click propagation.
    fireEvent.click(screen.getByText("建立使用者"));
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
    fireEvent.keyDown(backdrop, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("strips non-digits and caps the phone input at 10 chars (replaceAll handler)", () => {
    renderModal();
    const phone = screen.getByPlaceholderText("例:0912345678") as HTMLInputElement;
    fireEvent.change(phone, { target: { value: "09-12 (345) 678 99999" } });
    // All non-digits removed, then sliced to first 10 digits.
    expect(phone.value).toBe("0912345678");
  });

  it("submits with the cleaned digits-only phone payload", async () => {
    const { onCreated } = renderModal();

    // Target the phone field by its placeholder; submit cleans it to digits-only.
    fireEvent.change(screen.getByPlaceholderText("例:0912345678"), {
      target: { value: "abc0912345678def" },
    });

    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);

    await waitFor(() => expect(createMock).toHaveBeenCalledTimes(1));
    const payload = createMock.mock.calls[0][0];
    expect(payload.phoneNumber).toBe("0912345678");
    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
  });

  it("rejects a phone that is not exactly 10 digits without calling the API", async () => {
    renderModal();
    fireEvent.change(screen.getByPlaceholderText("例:0912345678"), {
      target: { value: "12345" },
    });
    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);

    expect(await screen.findByText("電話需為 10 位數字")).toBeInTheDocument();
    expect(createMock).not.toHaveBeenCalled();
  });

  it("submits with phoneNumber undefined when the phone field is left blank", async () => {
    renderModal();
    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(createMock).toHaveBeenCalledTimes(1));
    expect(createMock.mock.calls[0][0].phoneNumber).toBeUndefined();
  });

  it("surfaces the API error message on a failed create", async () => {
    createMock.mockRejectedValue({
      response: { data: { error: { message: "Email 已存在" } } },
    });
    renderModal();
    fireEvent.submit(screen.getByRole("dialog").querySelector("form") as HTMLFormElement);
    expect(await screen.findByText("Email 已存在")).toBeInTheDocument();
  });

  it("calls onClose when the 取消 button is clicked", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByText("取消"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
