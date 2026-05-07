import React, { useState, useEffect } from "react";
import { 
  UserCheck, 
  Users, 
  Clock, 
  UserPlus, 
  CheckCircle, 
  PhoneCall, 
  Award,
  Filter,
  RefreshCw,
  Search
} from "lucide-react";
import { apiService } from "../services/apiService";
import type { Lead } from "../types";
import { formatDateTime, formatPhoneNumber } from "../utils/formatters";
import { LANGUAGE_MAP } from "../utils/constants";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";

const AVAILABLE_RMS = ["Rajesh Kumar", "Priya Singh", "Amit Patel", "Sneha Gupta"];

export const RMPage: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRmFilter, setSelectedRmFilter] = useState("all");
  const [selectedLeadForAssign, setSelectedLeadForAssign] = useState<Lead | null>(null);
  const [assigningRm, setAssigningRm] = useState("");
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [selectedLeadForConvert, setSelectedLeadForConvert] = useState<Lead | null>(null);
  const [conversionNotes, setConversionNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Load hot leads
  const fetchHotLeads = async () => {
    setLoading(true);
    try {
      // Get leads with Hot classification
      const response = await apiService.getLeads({
        classification: ["Hot"]
      }, { page: 1, limit: 100 });
      
      setLeads(response.data);
    } catch (error) {
      console.error("Failed to load hot leads:", error);
      toast.error("Failed to fetch HOT leads");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHotLeads();
  }, []);

  // Filter leads
  const filteredLeads = leads.filter(lead => {
    const matchesSearch = 
      lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.phone.includes(searchTerm) ||
      (lead.email && lead.email.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const assignedRm = lead.rmAssignment?.rmName || "";
    const matchesRm = 
      selectedRmFilter === "all" ||
      (selectedRmFilter === "unassigned" && !assignedRm) ||
      (selectedRmFilter === "assigned" && assignedRm) ||
      assignedRm === selectedRmFilter;

    return matchesSearch && matchesRm;
  });

  // Calculate statistics
  const totalHotLeads = leads.length;
  const assignedLeadsCount = leads.filter(l => l.rmAssignment?.rmName).length;
  const unassignedLeadsCount = totalHotLeads - assignedLeadsCount;
  const convertedLeadsCount = leads.filter(l => l.status === "Completed" || l.rmAssignment?.converted).length;

  const handleAssignClick = (lead: Lead) => {
    setSelectedLeadForAssign(lead);
    setAssigningRm(lead.rmAssignment?.rmName || AVAILABLE_RMS[0]);
    setShowAssignModal(true);
  };

  const handleAssignSubmit = async () => {
    if (!selectedLeadForAssign) return;
    setSubmitting(true);
    try {
      await apiService.assignLead({
        lead_id: selectedLeadForAssign.id,
        rm_name: assigningRm
      });
      toast.success(`Assigned ${selectedLeadForAssign.name} to ${assigningRm}`);
      setShowAssignModal(false);
      fetchHotLeads();
    } catch (error) {
      console.error("Failed to assign RM:", error);
      toast.error("Failed to assign Relationship Manager");
    } finally {
      setSubmitting(false);
    }
  };

  const handleConvertClick = (lead: Lead) => {
    setSelectedLeadForConvert(lead);
    setConversionNotes("");
    setShowConvertModal(true);
  };

  const handleConvertSubmit = async () => {
    if (!selectedLeadForConvert) return;
    setSubmitting(true);
    const rmName = selectedLeadForConvert.rmAssignment?.rmName || "Auto";
    try {
      await apiService.markLeadConverted(rmName, selectedLeadForConvert.id, {
        notes: conversionNotes
      });
      toast.success(`${selectedLeadForConvert.name} marked as converted! 🎉`);
      setShowConvertModal(false);
      fetchHotLeads();
    } catch (error) {
      console.error("Failed to mark converted:", error);
      toast.error("Failed to mark lead as converted");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2">
            RM Desk <span className="text-sm font-semibold bg-red-100 text-red-700 px-3 py-1 rounded-full border border-red-200">ADMIN CONTROL</span>
          </h1>
          <p className="text-gray-500 mt-1">Supervise and allocate high-intent HOT leads directly to Relationship Managers.</p>
        </div>
        <button
          onClick={fetchHotLeads}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-550 text-white font-medium rounded-xl hover:bg-indigo-600 transition-all duration-200 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 active:scale-95 disabled:opacity-50"
          style={{ backgroundColor: "#4f46e5" }}
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          Refresh Desk
        </button>
      </div>

      {/* Stats Panel */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total HOT Leads", value: totalHotLeads, icon: Users, color: "from-red-500 to-rose-600", text: "text-rose-600", bg: "bg-rose-50" },
          { label: "Pending Allocation", value: unassignedLeadsCount, icon: Clock, color: "from-amber-400 to-orange-500", text: "text-amber-600", bg: "bg-amber-50" },
          { label: "Assigned to RMs", value: assignedLeadsCount, icon: UserCheck, color: "from-indigo-500 to-purple-600", text: "text-indigo-600", bg: "bg-indigo-50" },
          { label: "Converted Deals", value: convertedLeadsCount, icon: Award, color: "from-emerald-400 to-teal-500", text: "text-emerald-600", bg: "bg-emerald-50" }
        ].map((stat, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between hover:shadow-md transition-shadow"
          >
            <div>
              <p className="text-sm font-medium text-gray-500">{stat.label}</p>
              <h3 className="text-3xl font-extrabold text-gray-900 mt-1">{stat.value}</h3>
            </div>
            <div className={`p-3.5 rounded-2xl ${stat.bg} ${stat.text}`}>
              <stat.icon size={26} />
            </div>
          </motion.div>
        ))}
      </div>

      {/* Controls */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search leads by name, phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          />
        </div>

        {/* RM Assignment Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-gray-500 flex items-center gap-1.5">
            <Filter size={16} /> Filter:
          </span>
          <div className="flex rounded-xl p-1 bg-gray-50 border border-gray-100">
            {[
              { id: "all", label: "All" },
              { id: "unassigned", label: "Unassigned" },
              { id: "assigned", label: "Assigned" },
              ...AVAILABLE_RMS.map(name => ({ id: name, label: name.split(" ")[0] }))
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedRmFilter(tab.id)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-200 ${
                  selectedRmFilter === tab.id 
                    ? "bg-white text-indigo-600 shadow-sm" 
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-20 text-center flex flex-col items-center justify-center space-y-3">
            <RefreshCw size={36} className="animate-spin text-indigo-500" />
            <p className="text-gray-500 text-sm font-medium">Loading hot leads queue...</p>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="py-20 text-center flex flex-col items-center justify-center space-y-3">
            <Users size={48} className="text-gray-300" />
            <h3 className="text-lg font-bold text-gray-700">No HOT Leads Found</h3>
            <p className="text-gray-400 text-sm max-w-sm">No hot leads match your filters. Unassigned HOT leads will appear here as soon as they complete calls and get scored.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Lead Info</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Preferred Language</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Engagement / Intent Score</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Assigned RM</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredLeads.map((lead) => {
                  const score = lead.currentScore;
                  const isAssigned = !!lead.rmAssignment?.rmName;
                  const isConverted = lead.status === "Completed" || lead.rmAssignment?.converted;
                  
                  return (
                    <motion.tr 
                      key={lead.id} 
                      className="hover:bg-gray-50/50 transition-colors"
                      layoutId={`lead-${lead.id}`}
                    >
                      {/* Info */}
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-semibold text-gray-950 text-base">{lead.name}</p>
                          <p className="text-sm text-gray-500 mt-0.5">{formatPhoneNumber(lead.phone)}</p>
                          {lead.email && <p className="text-xs text-gray-400 mt-0.5">{lead.email}</p>}
                        </div>
                      </td>

                      {/* Language */}
                      <td className="px-6 py-4">
                        <span className="text-sm font-semibold bg-gray-100 text-gray-700 px-3 py-1 rounded-full border border-gray-200">
                          {LANGUAGE_MAP[lead.language as keyof typeof LANGUAGE_MAP] || lead.language}
                        </span>
                      </td>

                      {/* Score */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-24 bg-gray-100 h-2 rounded-full overflow-hidden">
                            <div 
                              className="bg-red-500 h-full rounded-full" 
                              style={{ width: `${(score?.compositeScore || 0) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-extrabold text-red-600">
                            {score ? `${Math.round(score.compositeScore * 100)}%` : "Unscored"}
                          </span>
                        </div>
                      </td>

                      {/* Assigned RM */}
                      <td className="px-6 py-4">
                        {isAssigned ? (
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-xs uppercase">
                              {lead.rmAssignment?.rmName.split(" ").map(n => n[0]).join("")}
                            </div>
                            <div>
                              <p className="text-sm font-bold text-gray-800">{lead.rmAssignment?.rmName}</p>
                              <p className="text-xs text-gray-400">Assigned {lead.rmAssignment?.assignedAt ? formatDateTime(lead.rmAssignment.assignedAt).split(",")[0] : ""}</p>
                            </div>
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-600 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200 animate-pulse">
                            <Clock size={12} /> Pending RM
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4">
                        {isConverted ? (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                            <CheckCircle size={12} /> Converted
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200">
                            <PhoneCall size={12} /> Live / In-Progress
                          </span>
                        )}
                      </td>

                      {/* Action buttons */}
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleAssignClick(lead)}
                            disabled={isConverted}
                            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 text-xs font-bold rounded-xl border border-indigo-150 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <UserPlus size={14} />
                            {isAssigned ? "Re-assign" : "Allocate RM"}
                          </button>
                          
                          <button
                            onClick={() => handleConvertClick(lead)}
                            disabled={isConverted}
                            className="flex items-center gap-1 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-600 text-xs font-bold rounded-xl border border-emerald-150 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <CheckCircle size={14} />
                            Mark Converted
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Allocation Modal */}
      <AnimatePresence>
        {showAssignModal && selectedLeadForAssign && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 shadow-xl max-w-md w-full border border-gray-100 space-y-5"
            >
              <div>
                <h3 className="text-xl font-extrabold text-gray-900">Allocate Relationship Manager</h3>
                <p className="text-sm text-gray-500 mt-1">Select an active RM to manage <strong>{selectedLeadForAssign.name}</strong>.</p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wide">Select Manager</label>
                <select
                  value={assigningRm}
                  onChange={(e) => setAssigningRm(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-medium bg-white"
                >
                  {AVAILABLE_RMS.map(name => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 justify-end pt-2">
                <button
                  onClick={() => setShowAssignModal(false)}
                  disabled={submitting}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-xl text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignSubmit}
                  disabled={submitting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl text-sm transition-all shadow-md active:scale-95 disabled:opacity-50"
                  style={{ backgroundColor: "#4f46e5" }}
                >
                  {submitting ? "Allocating..." : "Confirm Assignment"}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Conversion Modal */}
      <AnimatePresence>
        {showConvertModal && selectedLeadForConvert && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 shadow-xl max-w-md w-full border border-gray-100 space-y-5"
            >
              <div>
                <h3 className="text-xl font-extrabold text-gray-900 flex items-center gap-2">
                  🎉 Mark Lead as Converted
                </h3>
                <p className="text-sm text-gray-500 mt-1">Are you sure you want to mark <strong>{selectedLeadForConvert.name}</strong> as successfully converted?</p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wide">Closing / Conversion Notes</label>
                <textarea
                  value={conversionNotes}
                  onChange={(e) => setConversionNotes(e.target.value)}
                  placeholder="E.g. Customer agreed to ₹50k loan with 8% interest rate. App installed."
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                />
              </div>

              <div className="flex gap-3 justify-end pt-2">
                <button
                  onClick={() => setShowConvertModal(false)}
                  disabled={submitting}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-xl text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConvertSubmit}
                  disabled={submitting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition-all shadow-md active:scale-95 disabled:opacity-50"
                  style={{ backgroundColor: "#10b981" }}
                >
                  {submitting ? "Saving..." : "Confirm Conversion"}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default RMPage;
