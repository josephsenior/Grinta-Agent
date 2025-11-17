import { fireEvent, render, renderHook } from "@testing-library/react";
import React from "react";
import { act } from "react";
import { describe, expect, it, vi } from "vitest";

import { useInfiniteScroll } from "#/hooks/use-infinite-scroll";

type Options = Parameters<typeof useInfiniteScroll>[0];

const HookComponent: React.FC<Options> = (props) => {
  const ref = useInfiniteScroll(props);
  return <div data-testid="scroll-container" ref={ref} />;
};

const attachMetrics = (element: HTMLDivElement) => {
  let scrollTop = 0;
  let scrollHeight = 1000;
  let clientHeight = 400;

  Object.defineProperty(element, "scrollTop", {
    get: () => scrollTop,
    set: (value: number) => {
      scrollTop = value;
    },
    configurable: true,
  });

  Object.defineProperty(element, "scrollHeight", {
    get: () => scrollHeight,
    set: (value: number) => {
      scrollHeight = value;
    },
    configurable: true,
  });

  Object.defineProperty(element, "clientHeight", {
    get: () => clientHeight,
    set: (value: number) => {
      clientHeight = value;
    },
    configurable: true,
  });

  return {
    setScrollTop: (value: number) => {
      scrollTop = value;
    },
    setScrollHeight: (value: number) => {
      scrollHeight = value;
    },
    setClientHeight: (value: number) => {
      clientHeight = value;
    },
  };
};

describe("useInfiniteScroll", () => {
  it("fetches next page when near bottom", async () => {
    const fetchNextPage = vi.fn();
    const props: Options = {
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
      threshold: 50,
    };

    const { getByTestId } = render(<HookComponent {...props} />);
    const container = getByTestId("scroll-container") as HTMLDivElement;
    const metrics = attachMetrics(container);

    await act(async () => {});

    metrics.setScrollTop(1000 - 400 - 40);
    await act(async () => {
      fireEvent.scroll(container);
    });

    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it("skips fetching when already fetching or no next page", async () => {
    const fetchNextPage = vi.fn();
    const props: Options = {
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
      threshold: 30,
    };

    const { rerender, getByTestId } = render(<HookComponent {...props} />);
    const container = getByTestId("scroll-container") as HTMLDivElement;
    const metrics = attachMetrics(container);

    await act(async () => {});

    metrics.setScrollTop(1000 - 400 - 20);
    await act(async () => {
      fireEvent.scroll(container);
    });

    expect(fetchNextPage).toHaveBeenCalledTimes(1);
    fetchNextPage.mockClear();

    rerender(
      <HookComponent
        hasNextPage
        isFetchingNextPage
        fetchNextPage={fetchNextPage}
        threshold={30}
      />,
    );

    await act(async () => {});

    metrics.setScrollTop(1000 - 400 - 10);
    await act(async () => {
      fireEvent.scroll(container);
    });

    expect(fetchNextPage).not.toHaveBeenCalled();

    rerender(
      <HookComponent
        hasNextPage={false}
        isFetchingNextPage={false}
        fetchNextPage={fetchNextPage}
        threshold={30}
      />,
    );

    await act(async () => {});

    metrics.setScrollTop(1000 - 400 - 10);
    await act(async () => {
      fireEvent.scroll(container);
    });

    expect(fetchNextPage).not.toHaveBeenCalled();
  });

  it("cleans up scroll listener on unmount", async () => {
    const fetchNextPage = () => {};
    const addSpy = vi.spyOn(HTMLElement.prototype, "addEventListener");
    const removeSpy = vi.spyOn(HTMLElement.prototype, "removeEventListener");

    const { unmount, getByTestId } = render(
      <HookComponent
        hasNextPage
        isFetchingNextPage={false}
        fetchNextPage={fetchNextPage}
      />,
    );

    const container = getByTestId("scroll-container") as HTMLDivElement;
    attachMetrics(container);

    await act(async () => {});

    const handler = addSpy.mock.calls.find((call) => call[0] === "scroll")?.[1] as
      | EventListener
      | undefined;

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("scroll", handler);

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it("handles missing container without errors", () => {
    const fetchNextPage = vi.fn();

    const { unmount } = renderHook(() =>
      useInfiniteScroll({
        hasNextPage: true,
        isFetchingNextPage: false,
        fetchNextPage,
      }),
    );

    expect(fetchNextPage).not.toHaveBeenCalled();
    unmount();
  });
});
