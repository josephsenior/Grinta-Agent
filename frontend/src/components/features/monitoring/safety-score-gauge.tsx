import React, { useEffect, useState } from "react";

interface SafetyScoreGaugeProps {
  score: number; // 0-100
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function SafetyScoreGauge({
  score,
  label = "Safety Score",
  size = "md",
  className = "",
}: SafetyScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  // Animate score on mount and when it changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedScore(score);
    }, 100);
    return () => clearTimeout(timer);
  }, [score]);

  // Size configurations
  const sizeConfig = {
    sm: { radius: 40, strokeWidth: 8, fontSize: "text-xl" },
    md: { radius: 60, strokeWidth: 10, fontSize: "text-3xl" },
    lg: { radius: 80, strokeWidth: 12, fontSize: "text-4xl" },
  };

  const { radius, strokeWidth, fontSize } = sizeConfig[size];
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animatedScore / 100) * circumference;

  // Color based on score
  const getScoreColor = (value: number) => {
    if (value >= 80) return { stroke: "#10b981", text: "text-green-500" };
    if (value >= 60) return { stroke: "#f59e0b", text: "text-yellow-500" };
    if (value >= 40) return { stroke: "#f97316", text: "text-orange-500" };
    return { stroke: "#ef4444", text: "text-red-500" };
  };

  const { stroke, text } = getScoreColor(score);

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="relative">
        <svg
          width={radius * 2 + strokeWidth * 2}
          height={radius * 2 + strokeWidth * 2}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-gray-700"
          />
          
          {/* Animated progress circle */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            fill="none"
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
            style={{
              filter: `drop-shadow(0 0 8px ${stroke}40)`,
            }}
          />
        </svg>

        {/* Score text in center */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${fontSize} font-bold ${text}`}>
            {Math.round(animatedScore)}
          </span>
          <span className="text-xs text-gray-400 mt-1">/ 100</span>
        </div>
      </div>

      {/* Label */}
      <p className="text-sm text-gray-400 mt-3 font-medium">{label}</p>
    </div>
  );
}

