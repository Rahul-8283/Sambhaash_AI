/**
 * Constants and color mappings
 */

import { LeadStatus, LeadScore, CallStatus, UserRole } from "../types";

// Status colors
export const STATUS_COLORS: Record<LeadStatus | CallStatus | string, string> = {
  "Not Called": "bg-gray-100 text-gray-800",
  "Calling": "bg-blue-100 text-blue-800",
  "Connected": "bg-green-100 text-green-800",
  "No Answer": "bg-yellow-100 text-yellow-800",
  "Failed": "bg-red-100 text-red-800",
  "Completed": "bg-green-100 text-green-800",
};

// Score colors
export const SCORE_COLORS: Record<LeadScore, string> = {
  "Hot": "bg-red-100 text-red-800",
  "Warm": "bg-yellow-100 text-yellow-800",
  "Cold": "bg-blue-100 text-blue-800",
  "Unscored": "bg-gray-100 text-gray-800",
};

export const SCORE_ICONS: Record<LeadScore, string> = {
  "Hot": "🔥",
  "Warm": "🟡",
  "Cold": "❄️",
  "Unscored": "❓",
};

// Priority colors
export const PRIORITY_COLORS: Record<string, string> = {
  "High": "bg-red-100 text-red-800",
  "Medium": "bg-yellow-100 text-yellow-800",
  "Low": "bg-green-100 text-green-800",
};

// Sentiment colors
export const SENTIMENT_COLORS: Record<string, string> = {
  "Positive": "bg-green-100 text-green-800",
  "Neutral": "bg-gray-100 text-gray-800",
  "Negative": "bg-red-100 text-red-800",
};

// Tone options for prompt settings
export const TONE_OPTIONS = ["Formal", "Friendly", "Salesy"] as const;

// Language options
export const LANGUAGE_OPTIONS = [
  "English",
  "Hindi",
  "Hinglish",
  "Spanish",
  "French",
  "German",
  "Portuguese",
] as const;

// Lead source options
export const LEAD_SOURCE_OPTIONS = [
  "Facebook",
  "Website",
  "Email",
  "Referral",
  "Phone",
  "LinkedIn",
  "Other",
] as const;

// User role options
export const USER_ROLE_OPTIONS: UserRole[] = ["Campaign Manager", "AI Ops", "Business Owner"];

// Default pagination
export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

// LLM Provider options
export const LLM_PROVIDERS = ["OpenAI", "Groq"] as const;

// STT Provider options
export const STT_PROVIDERS = ["Whisper", "Deepgram"] as const;

// TTS Provider options
export const TTS_PROVIDERS = ["Sarvam", "Google"] as const;

// Sidebar items config
export const SIDEBAR_CONFIG = [
  {
    id: "leads",
    label: "Leads",
    path: "/dashboard/leads",
  },
  {
    id: "calls",
    label: "Calls",
    path: "/dashboard/calls",
  },
  {
    id: "analytics",
    label: "Analytics",
    path: "/dashboard/analytics",
  },
  {
    id: "campaigns",
    label: "Campaigns",
    path: "/dashboard/campaigns",
  },
  {
    id: "settings",
    label: "Settings",
    children: [
      { id: "prompt", label: "Prompt", path: "/dashboard/settings/prompt" },
      { id: "language", label: "Language", path: "/dashboard/settings/language" },
      { id: "retry", label: "Retry Logic", path: "/dashboard/settings/retry" },
      { id: "integrations", label: "Integrations", path: "/dashboard/settings/integrations" },
    ],
  },
  {
    id: "users",
    label: "Users",
    path: "/dashboard/users",
  },
];

// Toast duration (ms)
export const TOAST_DURATION = 3000;
