/**
 * Core Types for Sambhaash AI Admin Dashboard
 * Aligned with Backend Schema
 */

import type { ReactNode } from "react";

// ============ Lead Types ============
export type LeadStatus = "Not Called" | "Calling" | "Connected" | "No Answer" | "Failed" | "Completed";
export type ScoreClassification = "Hot" | "Warm" | "Cold" | "Unscored";
export type LeadPriority = "High" | "Medium" | "Low";

export interface ConversationTurn {
  role: "user" | "assistant";
  text: string;
  timestamp: string;
}

export interface LeadScore {
  id: string;
  leadId: string;
  callSessionId: string;
  interestScore: number;
  engagementScore: number;
  sentimentScore: number;
  compositeScore: number;
  classification: ScoreClassification;
  timestamp: string;
}

export interface RmAssignment {
  id: string;
  leadId: string;
  rmName: string;
  assignedAt: string;
  converted: boolean;
}

export interface CallSession {
  id: string;
  leadId: string;
  conversationHistory: ConversationTurn[];
  languageDetected: string;
  durationSeconds: number;
  createdAt: string;
}

export interface ObjectionLog {
  id: string;
  callSessionId: string;
  objectionType: string;
  objectionText: string;
  resolved: boolean;
  timestamp: string;
}

export interface Lead {
  id: string;
  phone: string;
  name: string;
  email?: string;
  language: string;
  status: LeadStatus;
  currentScore?: LeadScore;
  rmAssignment?: RmAssignment;
  createdAt: string;
}

export interface LeadWithDetails extends Lead {
  callSessions: CallSession[];
  scoreHistory: LeadScore[];
  objections: ObjectionLog[];
  totalCalls: number;
  lastCalledAt?: string;
}

export interface LeadFilters {
  status?: LeadStatus[];
  classification?: ScoreClassification[];
  rmAssignment?: string;
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
  callSessionId: string;
  leadId: string;
  leadName: string;
  leadPhone: string;
  duration: number;
  timestamp: string;
  status: CallStatus;
  transcript?: string;
  sentiment?: "Positive" | "Neutral" | "Negative";
  detectedObjections: ObjectionLog[];
  classification?: ScoreClassification;
  createdAt: string;
}

export interface CallFilters {
  status?: CallStatus[];
  leadId?: string;
  dateRange?: {
    start: string;
    end: string;
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

// ============ Analytics Types ============
export interface AnalyticsMetrics {
  totalLeads: number;
  callsMade: number;
  connectionRate: number;
  conversionRate: number;
  avgCallDuration: number;
  scoreDistribution: Record<ScoreClassification, number>;
}

export interface TimeSeriesData {
  date: string;
  value: number;
}

export interface ScoreDistribution {
  score: ScoreClassification;
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
  retryWindowStart: string;
  retryWindowEnd: string;
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

// ============ API Types ============
export interface PaginationParams {
  page: number;
  limit: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
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
}

export interface CreateUserFormData {
  name: string;
  email: string;
  role: UserRole;
}

export interface CreateCampaignFormData {
  name: string;
  description?: string;
  script?: string;
}

// ============ UI Helper Types ============
export interface TableColumn<T> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: unknown, row: T) => ReactNode;
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
  icon: ReactNode;
  badge?: number;
}
