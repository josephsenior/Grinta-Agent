import React, { ReactNode } from "react";
import EventLogger from "#/utils/event-logger";

const decodeHtmlEntities = (text: string): string => {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text;
  return textarea.value;
};

function MonoComponent(props: { children?: ReactNode }) {
  const { children } = props;

  const decodeString = (str: string): string => {
    try {
      return decodeHtmlEntities(str);
    } catch (e) {
      EventLogger.error(String(e));
      return str;
    }
  };

  if (Array.isArray(children)) {
    const processedChildren = children.map((child, idx) => {
      const k = `mono-${idx}`;
      if (typeof child === "string") {
        return (
          <span key={k} className="font-mono">
            {decodeString(child)}
          </span>
        );
      }

      if (React.isValidElement(child)) {
        return child.key != null
          ? child
          : React.cloneElement(child, { key: k });
      }

      return (
        <span key={k} className="font-mono">
          {String(child)}
        </span>
      );
    });

    return <strong className="font-mono">{processedChildren}</strong>;
  }

  if (typeof children === "string") {
    return <strong className="font-mono">{decodeString(children)}</strong>;
  }

  return <strong className="font-mono">{children}</strong>;
}

export { MonoComponent };
