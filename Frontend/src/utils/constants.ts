/**
 * Constants and color mappings
 */

import type { LeadStatus, ScoreClassification, UserRole } from "../types/index";

// Status colors - supports LeadStatus AND Call statuses
export const STATUS_COLORS: Record<LeadStatus | "Connected" | "No Answer" | "Failed" | string, string> = {
  "Not Called": "bg-[#faedcd]/40 text-[#3d2b1f]/70 border border-[#faedcd]",
  "Calling": "bg-[#d4a373]/20 text-[#d4a373] border border-[#d4a373]/30",
  "Connected": "bg-emerald-100/50 text-emerald-800 border border-emerald-200/50",
  "No Answer": "bg-amber-100/50 text-amber-800 border border-amber-200/50",
  "Failed": "bg-rose-100/50 text-rose-800 border border-rose-200/50",
  "Completed": "bg-emerald-100/50 text-emerald-800 border border-emerald-200/50",
};

// Score colors
export const SCORE_COLORS: Record<ScoreClassification, string> = {
  "Hot": "bg-rose-100/50 text-rose-800 border border-rose-200/50",
  "Warm": "bg-amber-100/50 text-amber-800 border border-amber-200/50",
  "Cold": "bg-blue-100/50 text-blue-800 border border-blue-200/50",
  "Unscored": "bg-[#faedcd]/40 text-[#3d2b1f]/70 border border-[#faedcd]",
};

export const SCORE_ICONS: Record<ScoreClassification, string> = {
  "Hot": "🔥",
  "Warm": "🟡",
  "Cold": "❄️",
  "Unscored": "❓",
};

// Priority colors
export const PRIORITY_COLORS: Record<string, string> = {
  "High": "bg-rose-100/50 text-rose-800 border border-rose-200/50",
  "Medium": "bg-amber-100/50 text-amber-800 border border-amber-200/50",
  "Low": "bg-emerald-100/50 text-emerald-800 border border-emerald-200/50",
};

// Sentiment colors
export const SENTIMENT_COLORS: Record<string, string> = {
  "Positive": "bg-emerald-100/50 text-emerald-800 border border-emerald-200/50",
  "Neutral": "bg-amber-100/50 text-amber-800 border border-amber-200/50",
  "Negative": "bg-rose-100/50 text-rose-800 border border-rose-200/50",
};

// Tone options for prompt settings
export const TONE_OPTIONS = ["Formal", "Friendly", "Salesy"] as const;

// Language options and mapping
export const LANGUAGE_MAP = {
  "English": "en",
  "Hindi": "hi",
  "Tamil": "ta",
  "Telugu": "te",
  "Kannada": "kn",
  "Malayalam": "ml",
  "Bengali": "bn",
  "Marathi": "mr",
  "Gujarati": "gu",
  "Punjabi": "pa",
} as const;

export const LANGUAGE_OPTIONS = [
  "English",
  "Hindi",
  "Tamil",
  "Telugu",
  "Kannada",
  "Malayalam",
  "Bengali",
  "Marathi",
  "Gujarati",
  "Punjabi",
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
    id: "analytics",
    label: "Analytics",
    path: "/dashboard/analytics",
  },
  {
    id: "settings",
    label: "Settings",
    children: [
      { id: "profile", label: "Profile", path: "/dashboard/settings/profile" },
      { id: "prompt", label: "Prompt", path: "/dashboard/settings/prompt" },
      { id: "language", label: "Language", path: "/dashboard/settings/language" },
      { id: "retry", label: "Retry Logic", path: "/dashboard/settings/retry" },
      { id: "integrations", label: "Integrations", path: "/dashboard/settings/integrations" },
    ],
  },
];

// Toast duration (ms)
export const TOAST_DURATION = 3000;
