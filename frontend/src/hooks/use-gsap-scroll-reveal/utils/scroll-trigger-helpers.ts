import { ScrollTrigger } from "gsap/ScrollTrigger";

function cleanupScrollTrigger(trigger: string | Element | HTMLElement) {
  ScrollTrigger.getAll().forEach((st) => {
    if (st.vars.trigger === trigger) {
      st.kill();
    }
  });
}

export function createScrollTriggerConfig(
  trigger: string | Element | HTMLElement,
  start: string,
  end: string,
  once: boolean,
  toggleActions: string,
  duration: number,
  delay: number,
) {
  const onEnterHandler = once
    ? () => {
        setTimeout(
          () => {
            cleanupScrollTrigger(trigger);
          },
          duration * 1000 + delay * 1000,
        );
      }
    : undefined;

  const finalToggleActions = once ? "play none none none" : toggleActions;

  return {
    trigger,
    start,
    end,
    toggleActions: finalToggleActions,
    onEnter: onEnterHandler,
  };
}

export { cleanupScrollTrigger };
