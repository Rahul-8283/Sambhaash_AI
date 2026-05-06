import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';

// ==================== TYPES & INTERFACES ====================

// --- Leads ---
export interface Lead {
  id: string;
  phone: string;
  name: string | null;
  email: string | null;
  language: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LeadCreate {
  phone: string;
  name?: string;
  email?: string;
  language?: string;
}

export interface LeadUpdate {
  name?: string;
  email?: string;
  language?: string;
  status?: string;
}

export interface LeadListResponse {
  total: number;
  limit: number;
  offset: number;
  leads: Lead[];
}

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

export interface RMLeaderboardEntry {
  rank: number;
  rm_name: string;
  total_assigned: number;
  converted: number;
  conversion_rate: number;
}

export interface RMLeaderboardResponse {
  period: string;
  total_rms: number;
  entries: RMLeaderboardEntry[];
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
    // Determine base URL - can be moved to environment variables later
    const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

    this.api = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
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
  public async getLeads(params?: { status?: string; limit?: number; offset?: number }): Promise<LeadListResponse> {
    const response: AxiosResponse<LeadListResponse> = await this.api.get('/api/leads', { params });
    return response.data;
  }

  public async getLead(id: string): Promise<Lead> {
    const response: AxiosResponse<Lead> = await this.api.get(`/api/leads/${id}`);
    return response.data;
  }

  public async createLead(lead: LeadCreate): Promise<Lead> {
    const response: AxiosResponse<Lead> = await this.api.post('/api/leads', lead);
    return response.data;
  }

  public async updateLead(id: string, lead: LeadUpdate): Promise<Lead> {
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
}

// Export a singleton instance
export const apiService = ApiService.getInstance();
