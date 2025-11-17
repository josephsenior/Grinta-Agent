import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useUserProviders } from "#/hooks/use-user-providers";
import { convertRawProvidersToList } from "#/utils/convert-raw-providers-to-list";

const useSettingsMock = vi.fn();

vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: () => useSettingsMock(),
}));

describe("useUserProviders", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("returns providers list derived from PROVIDER_TOKENS_SET", () => {
    const providerTokens = {
      github: "token-1",
      gitlab: null,
    };
    const converted = convertRawProvidersToList(providerTokens);
    useSettingsMock.mockReturnValue({ data: { PROVIDER_TOKENS_SET: providerTokens } });

    const { result } = renderHook(() => useUserProviders());

    expect(result.current.providers).toEqual(converted);
  });

  it("returns an empty list when settings are unavailable", () => {
    useSettingsMock.mockReturnValue({ data: undefined });

    const { result } = renderHook(() => useUserProviders());

    expect(result.current.providers).toEqual([]);
  });

  it("recomputes providers when PROVIDER_TOKENS_SET changes", () => {
    const firstTokens = { github: "token-1" };
    const secondTokens = { gitlab: "token-2" };

    useSettingsMock
      .mockReturnValueOnce({ data: { PROVIDER_TOKENS_SET: firstTokens } })
      .mockReturnValueOnce({ data: { PROVIDER_TOKENS_SET: secondTokens } });

    const { result, rerender } = renderHook(() => useUserProviders());

    expect(result.current.providers).toEqual(convertRawProvidersToList(firstTokens));

    rerender();
    expect(result.current.providers).toEqual(convertRawProvidersToList(secondTokens));
  });
});

