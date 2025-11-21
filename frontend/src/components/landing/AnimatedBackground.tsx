import React from "react";

export default function AnimatedBackground(): React.ReactElement {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none bg-[#000000]">
      {/* Simple subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0a] via-[#000000] to-[#000000]" />

      {/* Minimal subtle accent - single static orb */}
      <div className="absolute top-1/4 right-1/4 w-[400px] h-[400px] bg-[rgba(139,92,246,0.03)] rounded-full blur-3xl" />
    </div>
  );
}
