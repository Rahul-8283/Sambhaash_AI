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
        "bg-white rounded-lg border border-gray-200 shadow-sm",
        sizeClasses[size]
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 font-medium">{label}</p>
          <p
            className={clsx(
              "font-bold text-gray-900 mt-2",
              valueSizeClasses[size]
            )}
          >
            {value}
          </p>
          {trendValue && (
            <p
              className={clsx("text-xs mt-2 font-medium", {
                "text-green-600": trend === "up",
                "text-red-600": trend === "down",
                "text-gray-600": trend === "neutral",
              })}
            >
              {trend === "up" && "↑"} {trend === "down" && "↓"}{" "}
              {trendValue}
            </p>
          )}
        </div>
        {icon && <div className="text-gray-400 ml-4">{icon}</div>}
      </div>
    </div>
  );
};

export default MetricCard;
