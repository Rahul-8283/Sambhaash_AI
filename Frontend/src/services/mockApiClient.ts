/**
 * Mock API Client - Mirrors backend API contract
 * Uses realistic test data matching backend schema
 */

import type {
  Lead,
  LeadWithDetails,
  LeadFilters,
  LeadListResponse,
  Call,
  CallSession,
  CallFilters,
  CallListResponse,
  AnalyticsMetrics,
  PaginationParams,
  ObjectionLog,
  ScoreClassification,
  LeadStatus,
  ConversationTurn,
} from "../types";

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Mock data generators
const generateMockLeads = (count: number = 50): Lead[] => {
  const statuses: LeadStatus[] = [
    "Not Called", "Calling", "Connected", "No Answer", "Failed", "Completed",
  ];
  const languages = ["English", "Hindi", "Hinglish"];
  const rmNames = ["Rajesh Kumar", "Priya Singh", "Amit Patel", "Sneha Gupta"];

  return Array.from({ length: count }, (_, i) => {
    const score = Math.random();
    let classificationValue: ScoreClassification;
    if (score > 0.6) classificationValue = "Hot";
    else if (score > 0.4) classificationValue = "Warm";
    else if (score > 0.2) classificationValue = "Cold";
    else classificationValue = "Unscored";

    return {
      id: `lead-${i + 1}`,
      name: `Lead ${i + 1}`,
      phone: `+1${String(8005550000 + i).slice(0, 10)}`,
      email: `lead${i + 1}@example.com`,
      language: languages[Math.floor(Math.random() * languages.length)],
      status: statuses[Math.floor(Math.random() * statuses.length)],
      currentScore: {
        id: `score-${i + 1}`,
        leadId: `lead-${i + 1}`,
        callSessionId: `session-${i + 1}`,
        interestScore: Math.random() * 10,
        engagementScore: Math.random() * 10,
        sentimentScore: Math.random() * 2 - 1,
        compositeScore: Math.random() * 10,
        classification: classificationValue,
        timestamp: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      },
      rmAssignment: Math.random() > 0.4 ? {
        id: `rm-${i + 1}`,
        leadId: `lead-${i + 1}`,
        rmName: rmNames[Math.floor(Math.random() * rmNames.length)],
        assignedAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        converted: Math.random() > 0.7,
      } : undefined,
      createdAt: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000).toISOString(),
    };
  });
};

const generateMockCallSessions = (leadCount: number): CallSession[] => {
  const sessions: CallSession[] = [];
  for (let i = 0; i < Math.min(leadCount, 30); i++) {
    sessions.push({
      id: `session-${i + 1}`,
      leadId: `lead-${i + 1}`,
      conversationHistory: [
        { role: "assistant" as const, text: "Hello! How can I help you?", timestamp: new Date().toISOString() },
        { role: "user" as const, text: "I'm interested in your product.", timestamp: new Date().toISOString() },
        { role: "assistant" as const, text: "Great! Let me tell you more.", timestamp: new Date().toISOString() },
      ],
      languageDetected: "English",
      durationSeconds: Math.floor(Math.random() * 600) + 30,
      createdAt: new Date().toISOString(),
    });
  }
  return sessions;
};

const generateMockObjections = (): ObjectionLog[] => {
  const types = ["pricing", "timeline", "trust", "features", "competitors"];
  return Array.from({ length: 15 }, (_, i) => ({
    id: `objection-${i + 1}`,
    callSessionId: `session-${Math.floor(Math.random() * 30) + 1}`,
    objectionType: types[Math.floor(Math.random() * types.length)],
    objectionText: "This is a sample objection.",
    resolved: Math.random() > 0.4,
    timestamp: new Date().toISOString(),
  }));
};

const mockLeads = generateMockLeads(50);
const mockCallSessions = generateMockCallSessions(50);
const mockObjections = generateMockObjections();

const mockApiClient = {
  async getLeads(filters?: LeadFilters, pagination?: PaginationParams): Promise<LeadListResponse> {
    await delay(500);
    
    const page = pagination?.page || 1;
    const limit = pagination?.limit || 20;
    let filtered = [...mockLeads];

    if (filters?.status) {
      filtered = filtered.filter(l => filters.status!.includes(l.status));
    }
    if (filters?.classification) {
      filtered = filtered.filter(l => l.currentScore && filters.classification!.includes(l.currentScore.classification));
    }
    if (filters?.rmAssignment) {
      filtered = filtered.filter(l => l.rmAssignment?.rmName === filters.rmAssignment);
    }
    if (filters?.language) {
      filtered = filtered.filter(l => l.language === filters.language);
    }
    if (filters?.search) {
      const q = filters.search.toLowerCase();
      filtered = filtered.filter(l => 
        l.name.toLowerCase().includes(q) || 
        l.phone.includes(q) || 
        (l.email && l.email.toLowerCase().includes(q))
      );
    }

    const total = filtered.length;
    const startIdx = (page - 1) * limit;
    const data = filtered.slice(startIdx, startIdx + limit);

    return { data, total, page, limit };
  },

  async getLeadById(id: string): Promise<LeadWithDetails> {
    await delay(500);
    const lead = mockLeads.find(l => l.id === id);
    if (!lead) throw new Error("Lead not found");

    const callSessions = mockCallSessions.filter(s => s.leadId === id);
    const objections = mockObjections.filter(o => callSessions.some(s => s.id === o.callSessionId));

    return {
      ...lead,
      callSessions,
      scoreHistory: lead.currentScore ? [lead.currentScore] : [],
      objections,
      totalCalls: callSessions.length,
      lastCalledAt: callSessions[callSessions.length - 1]?.createdAt,
    };
  },

  async getCalls(filters?: CallFilters, pagination?: PaginationParams): Promise<CallListResponse> {
    await delay(500);
    
    const page = pagination?.page || 1;
    const limit = pagination?.limit || 20;

    const calls: Call[] = mockCallSessions.map((session, idx) => {
      const lead = mockLeads.find(l => l.id === session.leadId);
      const objections = mockObjections.filter(o => o.callSessionId === session.id);
      
      return {
        id: `call-${idx + 1}`,
        callSessionId: session.id,
        leadId: session.leadId,
        leadName: lead?.name || "Unknown",
        leadPhone: lead?.phone || "",
        duration: session.durationSeconds,
        timestamp: session.createdAt,
        status: (Math.random() > 0.3 ? "Connected" : (Math.random() > 0.5 ? "No Answer" : "Failed")) as any,
        transcript: session.conversationHistory.map((t: ConversationTurn) => `${t.role}: ${t.text}`).join("\n"),
        sentiment: Math.random() > 0.5 ? "Positive" : "Neutral" as any,
        detectedObjections: objections,
        classification: lead?.currentScore?.classification,
        createdAt: session.createdAt,
      };
    });

    let filtered = calls;
    if (filters?.status) {
      filtered = filtered.filter(c => filters.status!.includes(c.status));
    }
    if (filters?.leadId) {
      filtered = filtered.filter(c => c.leadId === filters.leadId);
    }

    const total = filtered.length;
    const startIdx = (page - 1) * limit;
    const data = filtered.slice(startIdx, startIdx + limit);

    return { data, total, page, limit };
  },

  async getAnalyticsMetrics(): Promise<AnalyticsMetrics> {
    await delay(500);
    const total = mockLeads.length;
    const connected = mockLeads.filter(l => l.status === "Connected").length;
    const converted = mockLeads.filter(l => l.rmAssignment?.converted).length;

    return {
      totalLeads: total,
      callsMade: mockCallSessions.length,
      connectionRate: total === 0 ? 0 : (connected / total) * 100,
      conversionRate: total === 0 ? 0 : (converted / total) * 100,
      avgCallDuration: mockCallSessions.length === 0 ? 0 : mockCallSessions.reduce((sum, s) => sum + s.durationSeconds, 0) / mockCallSessions.length,
      scoreDistribution: {
        "Hot": mockLeads.filter(l => l.currentScore?.classification === "Hot").length,
        "Warm": mockLeads.filter(l => l.currentScore?.classification === "Warm").length,
        "Cold": mockLeads.filter(l => l.currentScore?.classification === "Cold").length,
        "Unscored": mockLeads.filter(l => l.currentScore?.classification === "Unscored" || !l.currentScore).length,
      },
    };
  },

  async deleteLead(id: string): Promise<void> {
    await delay(300);
    const idx = mockLeads.findIndex(l => l.id === id);
    if (idx !== -1) mockLeads.splice(idx, 1);
  },
};

export default mockApiClient;
