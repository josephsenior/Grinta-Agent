import { gsap } from "gsap";

export function handleReducedMotion(element: HTMLElement) {
  const target = element.children.length > 0 ? element.children : element;
  gsap.set(target, {
    opacity: 1,
    y: 0,
    x: 0,
  });
}

export function calculateInitialPosition(
  from: "top" | "bottom" | "left" | "right",
  distance: number,
) {
  const initialY = (() => {
    if (from === "bottom") return distance;
    if (from === "top") return -distance;
    return 0;
  })();
  const initialX = (() => {
    if (from === "left") return -distance;
    if (from === "right") return distance;
    return 0;
  })();
  return { initialY, initialX };
}

export function setInitialState(
  target: HTMLElement | HTMLCollection,
  initialY: number,
  initialX: number,
) {
  gsap.set(target, {
    opacity: 0,
    y: initialY,
    x: initialX,
  });
}
