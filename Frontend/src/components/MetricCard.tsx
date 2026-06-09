/**
 * Reusable metric card component
 */

import React from "react";
import clsx from "clsx";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  size?: "sm" | "md" | "lg";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon,
  trend,
  trendValue,
  size = "md",
}) => {
  const sizeClasses = {
    sm: "p-4",
    md: "p-6",
    lg: "p-8",
  };

  const valueSizeClasses = {
    sm: "text-xl",
    md: "text-2xl",
    lg: "text-3xl",
  };

  return (
    <div
      className={clsx(
        "bg-[#faedcd]/20 border border-[#faedcd] shadow-premium rounded-2xl backdrop-blur-md",
        sizeClasses[size]
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs text-[#3d2b1f]/70 font-bold uppercase tracking-wider">{label}</p>
          <p
            className={clsx(
              "font-black text-[#2d1e18] mt-2 font-display",
              valueSizeClasses[size]
            )}
          >
            {value}
          </p>
          {trendValue && (
            <p
              className={clsx("text-xs mt-2 font-semibold", {
                "text-emerald-700": trend === "up",
                "text-rose-700": trend === "down",
                "text-[#3d2b1f]/70": trend === "neutral",
              })}
            >
              {trend === "up" && "↑"} {trend === "down" && "↓"}{" "}
              {trendValue}
            </p>
          )}
        </div>
        {icon && <div className="text-[#d4a373] ml-4">{icon}</div>}
      </div>
    </div>
  );
};

export default MetricCard;
