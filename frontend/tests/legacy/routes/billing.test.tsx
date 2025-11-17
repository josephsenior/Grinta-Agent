import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import BillingSettingsScreen from "#/routes/billing";
import { useSearchParams } from "react-router-dom";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";

vi.mock("react-router-dom", () => ({
  useSearchParams: vi.fn(),
}));

vi.mock("#/components/features/payment/payment-form", () => ({
  PaymentForm: () => <div data-testid="payment-form" />,
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: vi.fn(),
  displayErrorToast: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mockedUseSearchParams = vi.mocked(useSearchParams);
const successToast = vi.mocked(displaySuccessToast);
const errorToast = vi.mocked(displayErrorToast);

describe("BillingSettingsScreen", () => {
  beforeEach(() => {
    mockedUseSearchParams.mockReset();
    successToast.mockReset();
    errorToast.mockReset();
  });

  it("shows a success toast when checkout succeeds", async () => {
    const setSearchParams = vi.fn();
    mockedUseSearchParams.mockReturnValue([
      new URLSearchParams("checkout=success"),
      setSearchParams,
    ]);

    render(<BillingSettingsScreen />);

    await waitFor(() =>
      expect(successToast).toHaveBeenCalledWith("PAYMENT$SUCCESS"),
    );
    expect(errorToast).not.toHaveBeenCalled();
    expect(setSearchParams).toHaveBeenCalledWith({});
  });

  it("shows an error toast when checkout is cancelled", async () => {
    const setSearchParams = vi.fn();
    mockedUseSearchParams.mockReturnValue([
      new URLSearchParams("checkout=cancel"),
      setSearchParams,
    ]);

    render(<BillingSettingsScreen />);

    await waitFor(() =>
      expect(errorToast).toHaveBeenCalledWith("PAYMENT$CANCELLED"),
    );
    expect(successToast).not.toHaveBeenCalled();
    expect(setSearchParams).toHaveBeenCalledWith({});
  });

  it("renders the payment form without showing toasts when checkout param missing", async () => {
    const setSearchParams = vi.fn();
    mockedUseSearchParams.mockReturnValue([
      new URLSearchParams(""),
      setSearchParams,
    ]);

    const { getByTestId } = render(<BillingSettingsScreen />);

    expect(getByTestId("payment-form")).toBeInTheDocument();
    await waitFor(() => expect(setSearchParams).toHaveBeenCalledWith({}));
    expect(successToast).not.toHaveBeenCalled();
    expect(errorToast).not.toHaveBeenCalled();
  });
});

