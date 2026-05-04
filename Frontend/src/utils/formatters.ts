/**
 * Formatting utilities
 */

import { format, formatDistanceToNow } from "date-fns";

/**
 * Format phone number to standard format
 */
export function formatPhoneNumber(phone: string): string {
  const cleaned = phone.replace(/\D/g, "");
  if (cleaned.length === 10) {
    return `+1${cleaned}`;
  }
  if (cleaned.length === 11 && cleaned.startsWith("1")) {
    return `+${cleaned}`;
  }
  if (!cleaned.startsWith("+")) {
    return `+${cleaned}`;
  }
  return phone;
}

/**
 * Format date as readable string
 */
export function formatDate(date: string | Date): string {
  try {
    return format(new Date(date), "MMM d, yyyy");
  } catch {
    return "Invalid date";
  }
}

/**
 * Format date and time
 */
export function formatDateTime(date: string | Date): string {
  try {
    return format(new Date(date), "MMM d, yyyy HH:mm");
  } catch {
    return "Invalid date";
  }
}

/**
 * Format date relative to now (e.g., "2 hours ago")
 */
export function formatRelativeDate(date: string | Date): string {
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true });
  } catch {
    return "Invalid date";
  }
}

/**
 * Format duration in seconds to readable format (e.g., "1m 30s" or "45s")
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Format duration in seconds to total minutes with decimals
 */
export function formatDurationMinutes(seconds: number): string {
  const minutes = (seconds / 60).toFixed(1);
  return `${minutes}m`;
}

/**
 * Format percentage
 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format large numbers with commas
 */
export function formatNumber(value: number): string {
  return value.toLocaleString();
}

/**
 * Truncate text to specified length
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.substring(0, maxLength)}...`;
}

/**
 * Format time as HH:MM
 */
export function formatTime(hours: number, minutes: number): string {
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

/**
 * Parse time string "HH:MM" to { hours, minutes }
 */
export function parseTime(timeStr: string): { hours: number; minutes: number } {
  const [hours, minutes] = timeStr.split(":").map(Number);
  return { hours, minutes };
}

/**
 * Format score as display value
 */
export function formatScore(score: number): string {
  return `${score.toFixed(1)}/10`;
}
