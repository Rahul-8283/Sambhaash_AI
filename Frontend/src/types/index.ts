/**
 * Core Types for Sambhaash AI Admin Dashboard
 */

// ============ Lead Types ============
export type LeadStatus = "Not Called" | "Calling" | "Connected" | "No Answer" | "Failed" | "Completed";
export type LeadScore = "Hot" | "Warm" | "Cold" | "Unscored";
export type LeadPriority = "High" | "Medium" | "Low";

export interface Lead {
  id: string;
  name: string;
  phone: string;
  email?: string;
  language: string;
  source: string; // Facebook, website, etc.
  priority: LeadPriority;
  tags: string[];
  status: LeadStatus;
  score: LeadScore;
  scoreDetails?: {
    intent: number;
    engagement: number;
    sentiment: number;
    overall: number;
  };
  campaign?: string;
  lastCalled?: string; // ISO date
  totalCalls: number;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface LeadFilters {
  status?: LeadStatus[];
  score?: LeadScore[];
  dateRange?: {
    start: string;
    end: string;
  };
  campaign?: string;
  source?: string;
  language?: string;
  search?: string;
}

export interface LeadListResponse {
  data: Lead[];
  total: number;
  page: number;
  limit: number;
}

// ============ Call Types ============
export type CallStatus = "Connected" | "No Answer" | "Failed";

export interface Call {
  id: string;
  callSid: string;
  leadId: string;
  leadName: string;
  leadPhone: string;
  duration: number; // seconds
  timestamp: string; // ISO date
  status: CallStatus;
  retryCount: number;
  transcript?: string;
  recordingUrl?: string;
  sentiment?: "Positive" | "Neutral" | "Negative";
  detectedObjections?: string[];
  interestSignals?: string[];
  campaign?: string;
  createdAt: string;
}

export interface CallFilters {
  status?: CallStatus[];
  dateRange?: {
    start: string;
    end: string;
  };
  leadId?: string;
  campaign?: string;
  durationRange?: {
    min: number;
    max: number;
  };
}

export interface CallListResponse {
  data: Call[];
  total: number;
  page: number;
  limit: number;
}

// ============ Campaign Types ============
export interface Campaign {
  id: string;
  name: string;
  description?: string;
  leadCount: number;
  status: "Active" | "Paused" | "Completed";
  createdAt: string;
  updatedAt: string;
  script?: string;
}

export interface CampaignAnalytics {
  campaignId: string;
  campaignName: string;
  totalLeads: number;
  callsMade: number;
  connectionRate: number; // percentage
  conversionRate: number; // percentage
  avgCallDuration: number; // seconds
}

// ============ Analytics Types ============
export interface AnalyticsMetrics {
  totalLeads: number;
  callsMade: number;
  connectionRate: number; // percentage
  conversionRate: number; // percentage
  avgCallDuration: number; // seconds
  scoreDistribution: {
    hot: number;
    warm: number;
    cold: number;
    unscored: number;
  };
}

export interface TimeSeriesData {
  date: string;
  value: number;
}

export interface ScoreDistribution {
  score: LeadScore;
  count: number;
  percentage: number;
}

export interface StatusDistribution {
  status: LeadStatus;
  count: number;
  percentage: number;
}

// ============ User Types ============
export type UserRole = "Campaign Manager" | "AI Ops" | "Business Owner";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: "Active" | "Inactive";
  lastLogin?: string;
  createdAt: string;
}

// ============ Settings Types ============
export interface PromptSettings {
  systemPrompt: string;
  tone: "Formal" | "Friendly" | "Salesy";
  language: string;
  version: number;
  createdAt: string;
}

export interface LanguageSettings {
  defaultLanguage: string;
  autoDetect: boolean;
  supportedLanguages: string[];
}

export interface RetrySettings {
  maxRetries: number;
  retryDelayMinutes: number;
  retryWindowStart: string; // "HH:MM"
  retryWindowEnd: string; // "HH:MM"
}

export interface IntegrationSettings {
  twilio: {
    status: "Connected" | "Disconnected";
    phoneNumber?: string;
  };
  llm: {
    provider: "OpenAI" | "Groq";
    status: "Connected" | "Disconnected";
  };
  stt: {
    provider: "Whisper" | "Deepgram";
    status: "Connected" | "Disconnected";
  };
  tts: {
    provider: "Sarvam" | "Google";
    status: "Connected" | "Disconnected";
  };
}

// ============ API Request/Response Types ============
export interface PaginationParams {
  page: number;
  limit: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface ApiErrorResponse {
  error: string;
  statusCode: number;
  details?: Record<string, unknown>;
}

// ============ Form Types ============
export interface LeadUploadData {
  leads: Array<{
    name: string;
    phone: string;
    email?: string;
    language?: string;
    source?: string;
    priority?: LeadPriority;
    tags?: string[];
  }>;
}

export interface CreateLeadFormData {
  name: string;
  phone: string;
  email?: string;
  language: string;
  source: string;
  priority: LeadPriority;
  tags: string[];
}

export interface CreateCampaignFormData {
  name: string;
  description?: string;
  script?: string;
}

export interface CreateUserFormData {
  name: string;
  email: string;
  role: UserRole;
}

// ============ UI Helper Types ============
export interface TableColumn<T> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
  width?: string;
}

export interface BreadcrumbItem {
  label: string;
  path?: string;
}

export interface SidebarItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
  badge?: number;
}
