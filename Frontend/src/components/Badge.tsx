/**
 * Reusable Badge component for statuses, scores, etc.
 */

import React from "react";
import clsx from "clsx";
import { STATUS_COLORS, SCORE_COLORS, SCORE_ICONS, PRIORITY_COLORS } from "../../utils/constants";

interface BadgeProps {
  variant?: "status" | "score" | "priority" | "custom";
  value: string;
  customBgColor?: string;
  customTextColor?: string;
  showIcon?: boolean;
  size?: "sm" | "md" | "lg";
}

export const Badge: React.FC<BadgeProps> = ({
  variant = "custom",
  value,
  customBgColor,
  customTextColor,
  showIcon = false,
  size = "md",
}) => {
  let bgColor = customBgColor || "bg-gray-100";
  let textColor = customTextColor || "text-gray-800";
  let icon = "";

  if (variant === "status" && STATUS_COLORS[value]) {
    const colors = STATUS_COLORS[value];
    bgColor = colors.split(" ")[0];
    textColor = colors.split(" ")[1];
  } else if (variant === "score" && SCORE_COLORS[value as any]) {
    const colors = SCORE_COLORS[value as any];
    bgColor = colors.split(" ")[0];
    textColor = colors.split(" ")[1];
    if (showIcon) {
      icon = SCORE_ICONS[value as any] || "";
    }
  } else if (variant === "priority" && PRIORITY_COLORS[value]) {
    const colors = PRIORITY_COLORS[value];
    bgColor = colors.split(" ")[0];
    textColor = colors.split(" ")[1];
  }

  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        sizeClasses[size],
        bgColor,
        textColor
      )}
    >
      {icon && <span>{icon}</span>}
      {value}
    </span>
  );
};

export default Badge;
