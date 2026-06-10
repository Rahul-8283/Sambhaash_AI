import axios from 'axios';
import type {
  AxiosInstance,
  AxiosResponse,
  AxiosError,
} from 'axios';
import type { 
  Lead, 
  LeadFilters, 
  LeadListResponse, 
  LeadWithDetails,
  CreateLeadFormData
} from '../types';
import { supabase } from './supabase';

// ==================== ADDITIONAL TYPES ====================

export interface BatchUploadResponse {
  created: number;
  duplicates: number;
  errors: number;
  error_details: Array<{
    row?: number;
    index?: number;
    phone: string;
    error: string;
  }>;
}

// --- RM Management ---
export interface RMQueueLeadResponse {
  id: string;
  phone: string;
  name: string | null;
  email: string | null;
  language: string;
  status: string;
  latest_score: number | null;
  assigned_at: string;
}



export interface RMQueueResponse {
  rm_name: string;
  total: number;
  leads: RMQueueLeadResponse[];
}

export interface RMAssignRequest {
  lead_id: string;
  rm_name: string;
}

export interface RMAssignResponse {
  success: boolean;
  lead_id: string;
  rm_name: string;
  assigned_at: string;
}

export interface RMConvertRequest {
  notes?: string;
}

export interface RMConvertResponse {
  success: boolean;
  lead_id: string;
  rm_name: string;
  converted_at: string;
}

export interface RMStatsResponse {
  rm_name: string;
  total_assigned: number;
  converted: number;
  pending: number;
  conversion_rate: number;
}

// --- Queue & DLQ Management ---
export interface QueueStatsResponse {
  total_pending: number;
  active_workers: number;
  dlq_size: number;
}

export interface DlqJob {
  id: string;
  type: string;
  lead_id: string;
  payload: any;
  retry_count: number;
  status: string;
  created_at: string;
  updated_at: string;
  error?: string;
}

export interface RMLeaderboardEntry {
  rank: number;
  rm_name: string;
  total_assigned: number;
  converted: number;
  conversion_rate: number;
}

// --- Recordings Management ---
export interface RecordingMetadata {
  id: string;
  call_session_id: string;
  duration_seconds: number;
  file_size_bytes: number;
  storage_path: string;
  storage_url: string;
  language: string;
  sentiment: string;
  key_topics: string[];
  created_at: string;
}

export interface RecordingsListResponse {
  recordings: RecordingMetadata[];
  total: number;
  page: number;
  limit: number;
}

export interface RMLeaderboardResponse {
  period: string;
  total_rms: number;
  entries: RMLeaderboardEntry[];
  period_days?: number;
  leaderboard?: Array<{
    rm_name: string;
    total_leads: number;
    converted: number;
    conversion_rate: number;
  }>;
}

// --- General ---
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string | any;
}

// ==================== API SERVICE CLASS ====================

class ApiService {
  private api: AxiosInstance;
  private static instance: ApiService;

  private constructor() {
    // Determine base URL based on Vite's mode
    const isDev = import.meta.env.MODE === 'development';
    let baseURL = isDev ? import.meta.env.VITE_API_BASE_URL_DEV : import.meta.env.VITE_API_BASE_URL_PRO;

    // Dynamic production fallback if VITE_API_BASE_URL_PRO is undefined in environment
    if (!baseURL && typeof window !== 'undefined') {
      const protocol = window.location.protocol;
      const hostname = window.location.hostname;
      baseURL = `${protocol}//${hostname}:8000`;
    }

    this.api = axios.create({
      baseURL: baseURL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to attach Supabase auth token
    this.api.interceptors.request.use(async (config) => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
      }
      return config;
    });

    // Response interceptor for unified error handling
    this.api.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError) => {
        return Promise.reject(this.handleError(error));
      }
    );
  }

  public static getInstance(): ApiService {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService();
    }
    return ApiService.instance;
  }

  private handleError(error: AxiosError): ApiError {
    if (error.response?.data) {
      const data = error.response.data as any;
      return {
        status: error.response.status,
        message: data.detail || data.message || 'An error occurred',
        detail: data.detail,
      };
    }
    return {
      status: 500,
      message: error.message || 'An unexpected error occurred',
    };
  }

  // --- Health Endpoint ---
  public async checkHealth(): Promise<HealthResponse> {
    const response: AxiosResponse<HealthResponse> = await this.api.get('/health');
    return response.data;
  }

  // --- Leads Endpoints ---
  public async getLeads(filters?: LeadFilters, pagination?: { page?: number; limit?: number }): Promise<LeadListResponse> {
    const params = {
      ...filters,
      limit: pagination?.limit,
      offset: pagination?.page ? (pagination.page - 1) * (pagination.limit || 20) : undefined,
    };
    const response: AxiosResponse<any> = await this.api.get('/api/leads', { params });
    
    // Transform backend response to frontend LeadListResponse if necessary
    // Backend returns: { total, limit, offset, leads }
    // Frontend expects: { data: Lead[], total, page, limit }
    return {
      data: response.data?.leads || [],
      total: response.data?.total || 0,
      page: pagination?.page || 1,
      limit: response.data?.limit || 20
    };
  }

  public async getLead(id: string): Promise<LeadWithDetails> {
    const response: AxiosResponse<LeadWithDetails> = await this.api.get(`/api/leads/${id}`);
    return response.data;
  }

  public async createLead(lead: CreateLeadFormData): Promise<Lead> {
    const response: AxiosResponse<Lead> = await this.api.post('/api/leads', lead);
    return response.data;
  }

  public async updateLead(id: string, lead: Partial<CreateLeadFormData> & { status?: string }): Promise<Lead> {
    const response: AxiosResponse<Lead> = await this.api.put(`/api/leads/${id}`, lead);
    return response.data;
  }

  public async deleteLead(id: string): Promise<void> {
    await this.api.delete(`/api/leads/${id}`);
  }

  public async searchLeads(params: { phone?: string; email?: string }): Promise<{ count: number; results: Lead[] }> {
    const response: AxiosResponse<{ count: number; results: Lead[] }> = await this.api.get('/api/leads/search/query', { params });
    return response.data;
  }

  public async batchUploadCsv(file: File): Promise<BatchUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response: AxiosResponse<BatchUploadResponse> = await this.api.post('/api/leads/batch-upload/csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  public async batchUploadJson(file: File): Promise<BatchUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response: AxiosResponse<BatchUploadResponse> = await this.api.post('/api/leads/batch-upload/json', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  // --- RM Management Endpoints ---
  public async getRMQueue(rmName: string): Promise<RMQueueResponse> {
    const response: AxiosResponse<RMQueueResponse> = await this.api.get(`/api/rm/${rmName}/queue`);
    return response.data;
  }

  public async assignLead(assignment: RMAssignRequest): Promise<RMAssignResponse> {
    const response: AxiosResponse<RMAssignResponse> = await this.api.post('/api/rm/assign', assignment);
    return response.data;
  }

  public async markLeadConverted(rmName: string, leadId: string, data?: RMConvertRequest): Promise<RMConvertResponse> {
    const response: AxiosResponse<RMConvertResponse> = await this.api.post(`/api/rm/${rmName}/${leadId}/complete`, data);
    return response.data;
  }

  public async getRMDashboard(rmName: string, params?: { days?: number }): Promise<RMStatsResponse> {
    const response: AxiosResponse<RMStatsResponse> = await this.api.get(`/api/rm/${rmName}/dashboard`, { params });
    return response.data;
  }

  public async getRMLeaderboard(params?: { days?: number; limit?: number }): Promise<RMLeaderboardResponse> {
    const response: AxiosResponse<RMLeaderboardResponse> = await this.api.get('/api/rm/leaderboard', { params });
    return response.data;
  }

  // --- Knowledge Base (Admin) Endpoints ---
  public async uploadDocument(file: File, docType: string = 'appendix_a', language: string = 'hi'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const response: AxiosResponse<any> = await this.api.post('/admin/kb/upload', formData, {
      params: { doc_type: docType, language },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  public async listDocuments(): Promise<any[]> {
    const response: AxiosResponse<any[]> = await this.api.get('/admin/kb/documents');
    return response.data;
  }

  public async deleteDocument(docId: string): Promise<void> {
    await this.api.delete(`/admin/kb/documents/${docId}`);
  }

  public async searchKB(query: string, params?: { top_k?: number; language?: string }): Promise<any> {
    const response: AxiosResponse<any> = await this.api.get('/admin/kb/search', {
      params: { query, ...params },
    });
    return response.data;
  }

  public async getKBEffectiveness(days: number = 7): Promise<any> {
    const response: AxiosResponse<any> = await this.api.get('/admin/kb/analytics/effectiveness', {
      params: { limit_days: days },
    });
    return response.data;
  }

  // --- Queue & DLQ Endpoints ---
  public async getQueueStats(): Promise<QueueStatsResponse> {
    const response: AxiosResponse<QueueStatsResponse> = await this.api.get('/api/queue/stats');
    return response.data;
  }

  public async getDlqJobs(limit: number = 50): Promise<DlqJob[]> {
    const response: AxiosResponse<DlqJob[]> = await this.api.get('/api/queue/dlq', {
      params: { limit },
    });
    return response.data;
  }

  public async retryDlqJob(jobId: string): Promise<{ success: boolean; message: string }> {
    const response: AxiosResponse<{ success: boolean; message: string }> = await this.api.post(`/api/queue/dlq/${jobId}/retry`);
    return response.data;
  }

  // --- Recordings Endpoints ---
  public async getRecordings(page: number = 1, limit: number = 20): Promise<RecordingsListResponse> {
    const response: AxiosResponse<RecordingsListResponse> = await this.api.get('/admin/recordings', {
      params: { page, limit }
    });
    return response.data;
  }
}

// Export a singleton instance
export const apiService = ApiService.getInstance();
