/**
 * Leads management page - Phase 2
 * Shows lead list with filters, bulk actions, and upload
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Upload, Filter } from "lucide-react";
import { apiService } from "../services/apiService";
import type { Lead, LeadFilters } from "../types";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import Modal from "../components/Modal";
import { formatDateTime, formatPhoneNumber } from "../utils/formatters";
import { LANGUAGE_MAP } from "../utils/constants";

export const LeadsPage: React.FC = () => {
  const navigate = useNavigate();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedLeads, setSelectedLeads] = useState<Lead[]>([]);
  const [fileInputRef, setFileInputRef] = useState<HTMLInputElement | null>(null);

  // Create Lead form state
  const [createForm, setCreateForm] = useState({ name: "", phone: "", email: "", language: "en" });

  // Filters
  const [filters, setFilters] = useState<LeadFilters>({});
  const [searchQuery, setSearchQuery] = useState("");

  // Load leads
  useEffect(() => {
    const loadLeads = async () => {
      setLoading(true);
      try {
        const result = await apiService.getLeads(
          { ...filters, search: searchQuery || undefined },
          { page, limit: 20 }
        );
        setLeads(result.data);
        setTotal(result.total);
      } catch (error) {
        console.error("Failed to load leads:", error);
      } finally {
        setLoading(false);
      }
    };

    loadLeads();
  }, [page, filters, searchQuery]);

  const handleFilterChange = (key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
    setPage(1);
  };

  const handleRowClick = (lead: Lead) => {
    navigate(`/dashboard/leads/${lead.id}`);
  };

  const handleUploadClick = () => {
    fileInputRef?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setLoading(true);
    try {
      const response = await apiService.batchUploadCsv(file);
      alert(`Upload complete: ${response.created} leads created, ${response.duplicates} duplicates found.`);
      setShowUploadModal(false);
      // Refresh leads
      const result = await apiService.getLeads(filters, { page: 1, limit: 20 });
      setLeads(result.data);
      setTotal(result.total);
      setPage(1);
    } catch (error) {
      console.error("Error uploading CSV:", error);
      alert("Failed to upload leads. Please check the file format.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateLead = async () => {
    if (!createForm.name || !createForm.phone) {
      alert("Name and phone are required");
      return;
    }
    
    setLoading(true);
    try {
      await apiService.createLead({
        name: createForm.name,
        phone: createForm.phone,
        email: createForm.email,
        language: createForm.language,
      });
      
      setCreateForm({ name: "", phone: "", email: "", language: "en" });
      setShowCreateModal(false);
      
      // Refresh leads
      const result = await apiService.getLeads(filters, { page: 1, limit: 20 });
      setLeads(result.data);
      setTotal(result.total);
      setPage(1);
    } catch (error) {
      console.error("Error creating lead:", error);
      alert("Failed to create lead.");
    } finally {
      setLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedLeads.length === 0) return;
    if (!window.confirm(`Delete ${selectedLeads.length} selected lead(s)?`)) return;
    
    setLoading(true);
    try {
      await Promise.all(selectedLeads.map(lead => apiService.deleteLead(lead.id)));
      setSelectedLeads([]);
      // Refresh leads
      const result = await apiService.getLeads(filters, { page, limit: 20 });
      setLeads(result.data);
      setTotal(result.total);
    } catch (error) {
      console.error("Failed to delete leads:", error);
      alert("Failed to delete some leads.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6 pt-2 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-black text-[#2d1e18] font-display">Leads Queue</h1>
          <p className="text-sm font-semibold text-[#3d2b1f]/70">Track, manage, and engage {total} system leads</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-3 md:px-4 py-2 bg-[#faedcd] border border-[#d4a373]/30 text-[#3d2b1f] font-bold rounded-2xl hover:bg-[#faedcd]/80 transition-all shadow-sm text-sm cursor-pointer"
          >
            <Upload size={18} className="text-[#3d2b1f]/80" />
            Upload CSV
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-3 md:px-4 py-2 bg-[#d4a373] text-white font-bold rounded-2xl hover:bg-[#b5835a] transition-all shadow-lg shadow-[#d4a373]/20 text-sm cursor-pointer"
          >
            <Plus size={18} />
            Add Lead
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="glass rounded-3xl p-6 space-y-6 border border-[#faedcd]/60">
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Search by name, phone, or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2.5 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-[#3d2b1f] placeholder-[#3d2b1f]/40 font-medium"
          />
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#faedcd] text-[#3d2b1f] font-bold rounded-xl hover:bg-[#f5e3b8] transition-all shadow-sm"
          >
            <Filter size={20} className="text-[#3d2b1f]/80" />
            Filters
          </button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 pt-6 border-t border-[#faedcd]/80">
            {/* Status Filter */}
            <div>
              <label className="block text-xs font-bold text-[#3d2b1f]/80 uppercase tracking-wider mb-2">
                Status
              </label>
              <select
                value={(filters.status?.[0] as string) || ""}
                onChange={(e) =>
                  handleFilterChange("status", e.target.value ? [e.target.value] : undefined)
                }
                className="w-full px-3 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-[#3d2b1f] font-medium"
              >
                <option value="">All Statuses</option>
                <option value="Not Called">Not Called</option>
                <option value="Calling">Calling</option>
                <option value="Connected">Connected</option>
                <option value="No Answer">No Answer</option>
                <option value="Failed">Failed</option>
                <option value="Completed">Completed</option>
              </select>
            </div>

            {/* Score Filter */}
            <div>
              <label className="block text-xs font-bold text-[#3d2b1f]/80 uppercase tracking-wider mb-2">
                Score
              </label>
              <select
                value={(filters.classification?.[0] as string) || ""}
                onChange={(e) =>
                  handleFilterChange(
                    "classification",
                    e.target.value ? [e.target.value] : undefined
                  )
                }
                className="w-full px-3 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-[#3d2b1f] font-medium"
              >
                <option value="">All Scores</option>
                <option value="Hot">Hot 🔥</option>
                <option value="Warm">Warm 🟡</option>
                <option value="Cold">Cold ❄️</option>
                <option value="Unscored">Unscored ❓</option>
              </select>
            </div>

            {/* Language Filter */}
            <div>
              <label className="block text-xs font-bold text-[#3d2b1f]/80 uppercase tracking-wider mb-2">
                Language
              </label>
              <select
                value={filters.language || ""}
                onChange={(e) => handleFilterChange("language", e.target.value || undefined)}
                className="w-full px-3 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-[#3d2b1f] font-medium"
              >
                <option value="">All Languages</option>
                {Object.entries(LANGUAGE_MAP).map(([name, code]) => (
                  <option key={code} value={code}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            {/* RM Assignment Filter */}
            <div>
              <label className="block text-xs font-bold text-[#3d2b1f]/80 uppercase tracking-wider mb-2">
                RM Assigned
              </label>
              <select
                value={filters.rmAssignment || ""}
                onChange={(e) =>
                  handleFilterChange("rmAssignment", e.target.value || undefined)
                }
                className="w-full px-3 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-[#3d2b1f] font-medium"
              >
                <option value="">All RMs</option>
                <option value="Rajesh Kumar">Rajesh Kumar</option>
                <option value="Priya Singh">Priya Singh</option>
                <option value="Amit Patel">Amit Patel</option>
                <option value="Sneha Gupta">Sneha Gupta</option>
              </select>
            </div>

            {/* Clear Filters */}
            <div className="flex items-end">
              <button
                onClick={() => {
                  setFilters({});
                  setSearchQuery("");
                  setPage(1);
                }}
                className="w-full px-3 py-2 bg-[#faedcd] text-[#3d2b1f] font-bold rounded-xl hover:bg-[#f5e3b8] transition-colors shadow-sm"
              >
                Clear All
              </button>
            </div>
          </div>
        )}

        {/* Bulk Actions */}
        {selectedLeads.length > 0 && (
          <div className="flex items-center justify-between pt-4 border-t border-[#faedcd] bg-[#faedcd]/30 p-4 rounded-2xl border border-[#faedcd]/40">
            <p className="text-sm font-bold text-[#3d2b1f]">
              {selectedLeads.length} selected
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkDelete}
                className="px-4 py-2 bg-rose-600 text-white font-bold rounded-xl hover:bg-rose-700 transition-colors text-sm shadow-sm"
              >
                Delete Selected
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="glass rounded-3xl overflow-hidden border border-[#faedcd]/60 shadow-xl bg-white/40">
        {loading ? (
          <div className="p-8 text-center text-[#3d2b1f]/60 font-bold">Loading leads...</div>
        ) : leads.length === 0 ? (
          <div className="p-8 text-center text-[#3d2b1f]/60 font-bold">
            No leads found. Try adjusting your filters.
          </div>
        ) : (
          <>
            <DataTable
              data={leads}
              rowKey="id"
              onRowClick={handleRowClick}
              selectable
              onSelectionChange={setSelectedLeads}
              columns={[
                {
                  key: "name",
                  label: "Name",
                  sortable: true,
                  render: (value, row) => (
                    <div>
                      <p className="font-bold text-[#2d1e18]">{value as string}</p>
                      <p className="text-sm font-semibold text-[#3d2b1f]/60">
                        {(row as Lead).email}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "phone",
                  label: "Phone",
                  sortable: true,
                  render: (value) => <span className="font-semibold text-[#3d2b1f]/80">{formatPhoneNumber(value as string)}</span>,
                },
                {
                  key: "status",
                  label: "Status",
                  sortable: true,
                  render: (value) => (
                    <Badge variant="status" value={value as string} />
                  ),
                },
                {
                  key: "currentScore",
                  label: "Score",
                  sortable: false,
                  render: (value) => {
                    const score = value as any;
                    return (
                      <Badge
                        variant="score"
                        value={score?.classification || "Unscored"}
                        showIcon
                      />
                    );
                  },
                },
                {
                  key: "language",
                  label: "Language",
                  sortable: true,
                  render: (value) => {
                    const code = value as string;
                    const entry = Object.entries(LANGUAGE_MAP).find(([_, val]) => val === code);
                    return <span className="text-sm font-bold text-[#3d2b1f]/85">{entry ? entry[0] : code}</span>;
                  },
                },
                {
                  key: "rmAssignment",
                  label: "RM Assigned",
                  render: (value) => {
                    const rm = value as any;
                    return rm?.rmName ? (
                      <span className="text-sm font-bold text-[#3d2b1f]/90">{rm.rmName}</span>
                    ) : (
                      <span className="text-sm font-semibold text-[#3d2b1f]/40">—</span>
                    );
                  },
                },
                {
                  key: "createdAt",
                  label: "Added",
                  sortable: true,
                  render: (value) => (
                    <span className="text-sm font-semibold text-[#3d2b1f]/70">
                      {formatDateTime(value as string)}
                    </span>
                  ),
                },
              ]}
            />

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-[#faedcd]/60 bg-[#faedcd]/20">
              <p className="text-sm font-semibold text-[#3d2b1f]/70">
                Showing {total === 0 ? 0 : (page - 1) * 20 + 1} to {Math.min(page * 20, total)} of {total} leads
              </p>
              <div className="flex items-center gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                  className="px-4 py-2 bg-[#faedcd] border border-[#d4a373]/20 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#faedcd]/70 text-[#3d2b1f] font-bold transition-all shadow-sm cursor-pointer"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-sm font-bold text-[#3d2b1f]">Page {page}</span>
                <button
                  disabled={page * 20 >= total}
                  onClick={() => setPage(page + 1)}
                  className="px-4 py-2 bg-[#faedcd] border border-[#d4a373]/20 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#faedcd]/70 text-[#3d2b1f] font-bold transition-all shadow-sm cursor-pointer"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Upload Modal */}
      <Modal
        isOpen={showUploadModal}
        title="Upload Leads"
        onClose={() => setShowUploadModal(false)}
        actions={
          <>
            <button
              onClick={() => setShowUploadModal(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button onClick={handleUploadClick} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Upload
            </button>
            <input
              ref={setFileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
          </>
        }
      >
        <div className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <Upload size={32} className="mx-auto mb-2 text-gray-400" />
            <p className="text-sm font-medium text-gray-700">
              Drag and drop your CSV file here
            </p>
            <p className="text-xs text-gray-500 mt-1">
              or click to select from computer
            </p>
          </div>
          <p className="text-xs text-gray-600">
            <strong>Format:</strong> name, phone, email, language
          </p>
        </div>
      </Modal>

      {/* Create Lead Modal */}
      <Modal
        isOpen={showCreateModal}
        title="Add New Lead"
        onClose={() => setShowCreateModal(false)}
        actions={
          <>
            <button
              onClick={() => setShowCreateModal(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button onClick={handleCreateLead} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Create Lead
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone
            </label>
            <input
              type="tel"
              value={createForm.phone}
              onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={createForm.email}
              onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Language
            </label>
            <select
              value={createForm.language}
              onChange={(e) => setCreateForm({ ...createForm, language: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {Object.entries(LANGUAGE_MAP).map(([name, code]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default LeadsPage;
