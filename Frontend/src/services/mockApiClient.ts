/**
 * Mock API Client - Mirrors backend API contract
 * Use for frontend development while backend APIs are being finalized
 * Easy swap: import apiClient from '@/services/apiClient' when ready
 */

import {
  Lead,
  LeadFilters,
  LeadListResponse,
  Call,
  CallFilters,
  CallListResponse,
  Campaign,
  CampaignAnalytics,
  AnalyticsMetrics,
  TimeSeriesData,
  ScoreDistribution,
  StatusDistribution,
  User,
  PromptSettings,
  LanguageSettings,
  RetrySettings,
  IntegrationSettings,
  PaginationParams,
} from "../types";

// Mock data generators
const generateMockLeads = (count: number = 50): Lead[] => {
  const sources = ["Facebook", "Website", "Email", "Referral"];
  const statuses: ("Not Called" | "Calling" | "Connected" | "No Answer" | "Failed" | "Completed")[] = [
    "Not Called",
    "Calling",
    "Connected",
    "No Answer",
    "Failed",
    "Completed",
  ];
  const scores: ("Hot" | "Warm" | "Cold" | "Unscored")[] = ["Hot", "Warm", "Cold", "Unscored"];
  const priorities: ("High" | "Medium" | "Low")[] = ["High", "Medium", "Low"];
  const languages = ["English", "Hindi", "Hinglish"];

  return Array.from({ length: count }, (_, i) => ({
    id: `lead-${i + 1}`,
    name: `Lead ${i + 1}`,
    phone: `+1${String(8005550000 + i).slice(0, 10)}`,
    email: `lead${i + 1}@example.com`,
    language: languages[Math.floor(Math.random() * languages.length)],
    source: sources[Math.floor(Math.random() * sources.length)],
    priority: priorities[Math.floor(Math.random() * priorities.length)],
    tags: ["investor", "student", "prospect"][Math.floor(Math.random() * 3)].split(","),
    status: statuses[Math.floor(Math.random() * statuses.length)],
    score: scores[Math.floor(Math.random() * scores.length)],
    scoreDetails: {
      intent: Math.random() * 10,
      engagement: Math.random() * 10,
      sentiment: Math.random() * 10,
      overall: Math.random() * 10,
    },
    campaign: `Campaign ${Math.floor(Math.random() * 3) + 1}`,
    lastCalled: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    totalCalls: Math.floor(Math.random() * 5),
    notes: `Note for lead ${i + 1}`,
    createdAt: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date().toISOString(),
  }));
};

const generateMockCalls = (count: number = 30): Call[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: `call-${i + 1}`,
    callSid: `CA${Math.random().toString(36).substring(2, 15)}`,
    leadId: `lead-${Math.floor(Math.random() * 50) + 1}`,
    leadName: `Lead ${Math.floor(Math.random() * 50) + 1}`,
    leadPhone: `+1${String(8005550000 + Math.floor(Math.random() * 100)).slice(0, 10)}`,
    duration: Math.floor(Math.random() * 600) + 30,
    timestamp: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    status: ["Connected", "No Answer", "Failed"][Math.floor(Math.random() * 3)] as any,
    retryCount: Math.floor(Math.random() * 3),
    transcript: `This is a mock transcript for call ${i + 1}. The user discussed their interest in the product...`,
    recordingUrl: `https://example.com/recordings/call-${i + 1}.mp3`,
    sentiment: ["Positive", "Neutral", "Negative"][Math.floor(Math.random() * 3)] as any,
    detectedObjections: ["pricing", "timeline"],
    interestSignals: ["asked about features", "requested demo"],
    campaign: `Campaign ${Math.floor(Math.random() * 3) + 1}`,
    createdAt: new Date().toISOString(),
  }));
};

const generateMockCampaigns = (): Campaign[] => [
  {
    id: "camp-1",
    name: "Campaign 1",
    description: "First campaign",
    leadCount: 45,
    status: "Active",
    createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date().toISOString(),
    script: "Default script for campaign",
  },
  {
    id: "camp-2",
    name: "Campaign 2",
    description: "Second campaign",
    leadCount: 32,
    status: "Active",
    createdAt: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date().toISOString(),
    script: "Script for campaign 2",
  },
  {
    id: "camp-3",
    name: "Campaign 3",
    description: "Third campaign",
    leadCount: 28,
    status: "Paused",
    createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date().toISOString(),
    script: "Script for campaign 3",
  },
];

const generateMockUsers = (): User[] => [
  {
    id: "user-1",
    name: "Alice Manager",
    email: "alice@example.com",
    role: "Campaign Manager",
    status: "Active",
    lastLogin: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "user-2",
    name: "Bob Ops",
    email: "bob@example.com",
    role: "AI Ops",
    status: "Active",
    lastLogin: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 150 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "user-3",
    name: "Carol Owner",
    email: "carol@example.com",
    role: "Business Owner",
    status: "Active",
    lastLogin: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 200 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

// Store for mock data (in-memory)
let mockLeads = generateMockLeads(50);
let mockCalls = generateMockCalls(30);

// Simulate network delay
const delay = (ms: number = 500) => new Promise((resolve) => setTimeout(resolve, ms));

// ============ Lead API ============
export const mockApiClient = {
  // Leads
  async getLeads(
    filters?: LeadFilters,
    pagination?: PaginationParams
  ): Promise<LeadListResponse> {
    await delay();

    const page = pagination?.page || 1;
    const limit = pagination?.limit || 20;

    let filtered = [...mockLeads];

    if (filters?.status) {
      filtered = filtered.filter((l) => filters.status!.includes(l.status));
    }
    if (filters?.score) {
      filtered = filtered.filter((l) => filters.score!.includes(l.score));
    }
    if (filters?.campaign) {
      filtered = filtered.filter((l) => l.campaign === filters.campaign);
    }
    if (filters?.source) {
      filtered = filtered.filter((l) => l.source === filters.source);
    }
    if (filters?.language) {
      filtered = filtered.filter((l) => l.language === filters.language);
    }
    if (filters?.search) {
      const search = filters.search.toLowerCase();
      filtered = filtered.filter(
        (l) =>
          l.name.toLowerCase().includes(search) ||
          l.phone.includes(search) ||
          l.email?.toLowerCase().includes(search)
      );
    }

    const total = filtered.length;
    const start = (page - 1) * limit;
    const data = filtered.slice(start, start + limit);

    return { data, total, page, limit };
  },

  async getLeadById(id: string): Promise<Lead | null> {
    await delay();
    return mockLeads.find((l) => l.id === id) || null;
  },

  async createLead(lead: Omit<Lead, "id" | "createdAt" | "updatedAt">): Promise<Lead> {
    await delay();
    const newLead: Lead = {
      ...lead,
      id: `lead-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    mockLeads.push(newLead);
    return newLead;
  },

  async updateLead(id: string, updates: Partial<Lead>): Promise<Lead> {
    await delay();
    const index = mockLeads.findIndex((l) => l.id === id);
    if (index === -1) throw new Error("Lead not found");
    mockLeads[index] = { ...mockLeads[index], ...updates, updatedAt: new Date().toISOString() };
    return mockLeads[index];
  },

  async deleteLead(id: string): Promise<void> {
    await delay();
    mockLeads = mockLeads.filter((l) => l.id !== id);
  },

  async uploadLeads(leads: Omit<Lead, "id" | "createdAt" | "updatedAt">[]): Promise<Lead[]> {
    await delay();
    const created = leads.map((lead) => ({
      ...lead,
      id: `lead-${Date.now()}-${Math.random()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }));
    mockLeads.push(...created);
    return created;
  },

  // Calls
  async getCalls(filters?: CallFilters, pagination?: PaginationParams): Promise<CallListResponse> {
    await delay();

    const page = pagination?.page || 1;
    const limit = pagination?.limit || 20;

    let filtered = [...mockCalls];

    if (filters?.status) {
      filtered = filtered.filter((c) => filters.status!.includes(c.status));
    }
    if (filters?.leadId) {
      filtered = filtered.filter((c) => c.leadId === filters.leadId);
    }
    if (filters?.campaign) {
      filtered = filtered.filter((c) => c.campaign === filters.campaign);
    }

    const total = filtered.length;
    const start = (page - 1) * limit;
    const data = filtered.slice(start, start + limit).sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    return { data, total, page, limit };
  },

  async getCallById(id: string): Promise<Call | null> {
    await delay();
    return mockCalls.find((c) => c.id === id) || null;
  },

  // Analytics
  async getAnalyticsMetrics(): Promise<AnalyticsMetrics> {
    await delay();
    const totalLeads = mockLeads.length;
    const connectedCalls = mockCalls.filter((c) => c.status === "Connected").length;
    const callsMade = mockCalls.length;

    return {
      totalLeads,
      callsMade,
      connectionRate: callsMade > 0 ? (connectedCalls / callsMade) * 100 : 0,
      conversionRate: totalLeads > 0 ? (connectedCalls / totalLeads) * 100 : 0,
      avgCallDuration: callsMade > 0 ? mockCalls.reduce((s, c) => s + c.duration, 0) / callsMade : 0,
      scoreDistribution: {
        hot: mockLeads.filter((l) => l.score === "Hot").length,
        warm: mockLeads.filter((l) => l.score === "Warm").length,
        cold: mockLeads.filter((l) => l.score === "Cold").length,
        unscored: mockLeads.filter((l) => l.score === "Unscored").length,
      },
    };
  },

  async getCallsTimeSeries(days: number = 30): Promise<TimeSeriesData[]> {
    await delay();
    return Array.from({ length: days }, (_, i) => ({
      date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
      value: Math.floor(Math.random() * 20) + 5,
    }));
  },

  async getScoreDistribution(): Promise<ScoreDistribution[]> {
    await delay();
    const total = mockLeads.length;
    return [
      {
        score: "Hot",
        count: mockLeads.filter((l) => l.score === "Hot").length,
        percentage: (mockLeads.filter((l) => l.score === "Hot").length / total) * 100,
      },
      {
        score: "Warm",
        count: mockLeads.filter((l) => l.score === "Warm").length,
        percentage: (mockLeads.filter((l) => l.score === "Warm").length / total) * 100,
      },
      {
        score: "Cold",
        count: mockLeads.filter((l) => l.score === "Cold").length,
        percentage: (mockLeads.filter((l) => l.score === "Cold").length / total) * 100,
      },
      {
        score: "Unscored",
        count: mockLeads.filter((l) => l.score === "Unscored").length,
        percentage: (mockLeads.filter((l) => l.score === "Unscored").length / total) * 100,
      },
    ];
  },

  async getStatusDistribution(): Promise<StatusDistribution[]> {
    await delay();
    const total = mockLeads.length;
    const statuses: ("Not Called" | "Calling" | "Connected" | "No Answer" | "Failed" | "Completed")[] = [
      "Not Called",
      "Calling",
      "Connected",
      "No Answer",
      "Failed",
      "Completed",
    ];

    return statuses.map((status) => ({
      status,
      count: mockLeads.filter((l) => l.status === status).length,
      percentage: (mockLeads.filter((l) => l.status === status).length / total) * 100,
    }));
  },

  async getCampaignAnalytics(campaignId: string): Promise<CampaignAnalytics> {
    await delay();
    const campaignLeads = mockLeads.filter((l) => l.campaign === campaignId);
    const campaignCalls = mockCalls.filter((c) => c.campaign === campaignId);
    const connectedCalls = campaignCalls.filter((c) => c.status === "Connected").length;

    return {
      campaignId,
      campaignName: `Campaign ${campaignId}`,
      totalLeads: campaignLeads.length,
      callsMade: campaignCalls.length,
      connectionRate:
        campaignCalls.length > 0 ? (connectedCalls / campaignCalls.length) * 100 : 0,
      conversionRate:
        campaignLeads.length > 0 ? (connectedCalls / campaignLeads.length) * 100 : 0,
      avgCallDuration:
        campaignCalls.length > 0
          ? campaignCalls.reduce((s, c) => s + c.duration, 0) / campaignCalls.length
          : 0,
    };
  },

  // Campaigns
  async getCampaigns(): Promise<Campaign[]> {
    await delay();
    return generateMockCampaigns();
  },

  async getCampaignById(id: string): Promise<Campaign | null> {
    await delay();
    return generateMockCampaigns().find((c) => c.id === id) || null;
  },

  async createCampaign(campaign: Omit<Campaign, "id" | "createdAt" | "updatedAt">): Promise<Campaign> {
    await delay();
    return {
      ...campaign,
      id: `camp-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  },

  // Users
  async getUsers(): Promise<User[]> {
    await delay();
    return generateMockUsers();
  },

  async getUserById(id: string): Promise<User | null> {
    await delay();
    return generateMockUsers().find((u) => u.id === id) || null;
  },

  async createUser(user: Omit<User, "id" | "createdAt">): Promise<User> {
    await delay();
    return {
      ...user,
      id: `user-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
  },

  // Settings
  async getPromptSettings(): Promise<PromptSettings> {
    await delay();
    return {
      systemPrompt:
        "You are a helpful AI assistant. Your goal is to understand user needs and provide excellent support.",
      tone: "Friendly",
      language: "English",
      version: 1,
      createdAt: new Date().toISOString(),
    };
  },

  async updatePromptSettings(settings: Partial<PromptSettings>): Promise<PromptSettings> {
    await delay();
    return {
      ...settings,
      version: (settings.version || 0) + 1,
      createdAt: new Date().toISOString(),
    } as PromptSettings;
  },

  async getLanguageSettings(): Promise<LanguageSettings> {
    await delay();
    return {
      defaultLanguage: "English",
      autoDetect: true,
      supportedLanguages: ["English", "Hindi", "Hinglish", "Spanish"],
    };
  },

  async updateLanguageSettings(settings: LanguageSettings): Promise<LanguageSettings> {
    await delay();
    return settings;
  },

  async getRetrySettings(): Promise<RetrySettings> {
    await delay();
    return {
      maxRetries: 3,
      retryDelayMinutes: 30,
      retryWindowStart: "09:00",
      retryWindowEnd: "19:00",
    };
  },

  async updateRetrySettings(settings: RetrySettings): Promise<RetrySettings> {
    await delay();
    return settings;
  },

  async getIntegrationSettings(): Promise<IntegrationSettings> {
    await delay();
    return {
      twilio: {
        status: "Connected",
        phoneNumber: "+1-555-0123",
      },
      llm: {
        provider: "OpenAI",
        status: "Connected",
      },
      stt: {
        provider: "Whisper",
        status: "Connected",
      },
      tts: {
        provider: "Sarvam",
        status: "Connected",
      },
    };
  },

  async testIntegration(type: "twilio" | "llm" | "stt" | "tts"): Promise<{ status: "success" | "error"; message: string }> {
    await delay();
    return { status: "success", message: `${type} integration test successful` };
  },
};

export default mockApiClient;
