import React from "react";
import SvgFile from "#/icons/file.svg?react";

type Props = {
  ext?: string;
  statusClass?: "added" | "modified" | "deleted";
};

function sanitizeExt(ext?: string) {
  if (!ext) {
    return "";
  }
  const e = ext.replace(/[^a-zA-Z0-9]/g, "").slice(0, 6);
  return e.toUpperCase();
}

export default function ExtensionIcon({ ext, statusClass }: Props) {
  const label = sanitizeExt(ext);

  // choose base SVG (we keep same base for all; status tinting handled by parent CSS)
  return (
    <span className={`extension-icon ${statusClass ?? ""}`} aria-hidden>
      <span className="node-icon-svg">
        <SvgFile />
      </span>
      {label ? <span className="ext-pill">{label}</span> : null}
    </span>
  );
}
