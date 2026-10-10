/**
 * Lead detail page - shows single lead with call history, scores, and actions
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Phone, Mail, ChevronDown } from "lucide-react";
import toast from "react-hot-toast";
import { apiService } from "../services/apiService";
import type { ApiError } from "../services/apiService";
import type { LeadWithDetails, ScoreClassification } from "../types";
import Badge from "../components/Badge";
import { formatDateTime, formatPhoneNumber, formatDuration } from "../utils/formatters";
import { LANGUAGE_MAP } from "../utils/constants";
import MetricCard from "../components/MetricCard";

export const LeadDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [lead, setLead] = useState<LeadWithDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState("");
  const [savedNotes, setSavedNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [openSession, setOpenSession] = useState<string | null>(null);

  useEffect(() => {
    const loadLead = async () => {
      if (!id) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const result = await apiService.getLead(id);
        setLead(result);
        setNotes(result.notes ?? "");
        setSavedNotes(result.notes ?? "");
      } catch (error) {
        console.error("Failed to load lead:", error);
      } finally {
        setLoading(false);
      }
    };

    loadLead();
  }, [id]);

  if (loading) {
    return (
      <div className="p-6 text-center text-gray-500">Loading lead details...</div>
    );
  }

  if (!lead) {
    return (
      <div className="p-6 text-center text-gray-500">Lead not found</div>
    );
  }

  // The API returns score history newest first
  const latestScore = lead.scoreHistory?.[0] || lead.currentScore;

  // Scores are 0-1; show them as percentages
  const pct = (value: number) => `${Math.round(value * 100)}%`;

  // Classification each call produced, so a timeline row is not stamped with the lead's latest
  const classificationBySession = new Map<string, ScoreClassification>(
    (lead.scoreHistory ?? []).map((s) => [s.callSessionId, s.classification])
  );

  const saveNotes = async () => {
    if (!id) return;
    setSavingNotes(true);
    try {
      await apiService.updateLead(id, { notes });
      setSavedNotes(notes);
      toast.success("Notes saved");
    } catch (error) {
      toast.error((error as ApiError).message || "Failed to save notes");
    } finally {
      setSavingNotes(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <button
          onClick={() => navigate("/dashboard/leads")}
          className="flex items-center gap-2 text-[#d4a373] hover:text-[#b5835a] font-bold mb-4 bg-[#faedcd]/40 px-4 py-2 rounded-lg border border-[#faedcd] transition-all cursor-pointer shadow-sm"
        >
          <ArrowLeft size={20} />
          Back to Leads
        </button>
      </div>

      {/* Lead Info Card */}
      <div className="glass rounded-lg p-8 border border-[#faedcd]/60 shadow-xl">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-black text-[#2d1e18] font-display">{lead.name}</h1>
            <p className="text-sm font-semibold text-[#3d2b1f]/60 mt-1">Lead ID: {lead.id}</p>
          </div>
          <Badge variant="status" value={lead.status} size="lg" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 pt-6 border-t border-[#faedcd]">
          {/* Contact Info */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Phone size={20} className="text-[#d4a373]" />
              <div>
                <p className="text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wider">Phone</p>
                <p className="font-bold text-[#2d1e18] mt-0.5">{formatPhoneNumber(lead.phone)}</p>
              </div>
            </div>
            {lead.email && (
              <div className="flex items-center gap-3">
                <Mail size={20} className="text-[#d4a373]" />
                <div>
                  <p className="text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wider">Email</p>
                  <p className="font-bold text-[#2d1e18] mt-0.5">{lead.email}</p>
                </div>
              </div>
            )}
          </div>

          {/* Meta Info */}
          <div className="space-y-4">
            <div>
              <p className="text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wider">Language Preference</p>
              <p className="font-bold text-[#2d1e18] mt-0.5">
                {Object.entries(LANGUAGE_MAP).find(([_, val]) => val === lead.language)?.[0] || lead.language}
              </p>
            </div>
            <div>
              <p className="text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wider">Added to System</p>
              <p className="font-bold text-[#2d1e18] mt-0.5">{formatDateTime(lead.createdAt)}</p>
            </div>
          </div>
        </div>

        {/* RM Assignment */}
        {lead.rmAssignment && (
          <div className="mt-6 pt-6 border-t border-[#faedcd]">
            <p className="text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wider mb-2">Relationship Manager Assigned</p>
            <div className="flex items-center gap-3">
              <p className="font-bold text-[#2d1e18]">{lead.rmAssignment.rmName}</p>
              {lead.rmAssignment.converted && (
                <Badge variant="custom" customBgColor="bg-emerald-100/50" customTextColor="text-emerald-800 border border-emerald-200/50" value="Converted" size="sm" />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Scoring Metrics */}
      {latestScore && (
        <div className="space-y-4">
          <h2 className="text-xl font-black text-[#2d1e18] font-display">Lead Score Indicators</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard
              label="Overall Score"
              value={pct(latestScore.compositeScore)}
              size="md"
            />
            <MetricCard
              label="Interest Score"
              value={pct(latestScore.interestScore)}
              size="md"
            />
            <MetricCard
              label="Engagement Score"
              value={pct(latestScore.engagementScore)}
              size="md"
            />
            <MetricCard
              label="Sentiment Score"
              value={pct(latestScore.sentimentScore)}
              size="md"
            />
          </div>
          <div className="mt-4">
            <Badge
              variant="score"
              value={latestScore.classification}
              showIcon
              size="lg"
            />
          </div>
        </div>
      )}

      {/* Call History */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-black text-[#2d1e18] font-display">Call Timeline</h2>
          <button
            onClick={() => {
              if (lead.phone) {
                window.location.href = `tel:${lead.phone}`;
              }
            }}
            disabled={!lead.phone}
            className="flex items-center gap-2 px-4 py-2 bg-[#d4a373] text-white font-bold rounded-lg hover:bg-[#b5835a] disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-[#d4a373]/25 cursor-pointer transition-all active:scale-95 text-sm"
          >
            <Phone size={18} />
            Call Now
          </button>
        </div>

        {(!lead.callSessions || lead.callSessions.length === 0) ? (
          <div className="bg-[#faedcd]/15 rounded-lg border border-[#faedcd]/60 p-8 text-center text-[#3d2b1f]/60 font-semibold shadow-inner">
            No call records available
          </div>
        ) : (
          <div className="space-y-3">
            {lead.callSessions?.map((session) => {
              const sessionClass = classificationBySession.get(session.id);
              const turns = session.conversationHistory ?? [];
              const isOpen = openSession === session.id;
              const lastTurn = turns[turns.length - 1];
              return (
                <div
                  key={session.id}
                  className="bg-white/50 backdrop-blur-sm rounded-lg border border-[#faedcd]/60 p-5 hover:border-[#d4a373]/40 transition-all shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-[#2d1e18]">
                        Duration: {formatDuration(session.durationSeconds)}
                      </p>
                      <p className="text-xs font-semibold text-[#3d2b1f]/60 mt-1">
                        Called on {formatDateTime(session.createdAt)}
                      </p>
                      {session.languageDetected && (
                        <p className="text-xs font-semibold text-[#3d2b1f]/50 mt-1">
                          Detected language: {session.languageDetected}
                        </p>
                      )}
                    </div>
                    {sessionClass && (
                      <Badge variant="score" value={sessionClass} showIcon size="sm" />
                    )}
                  </div>

                  {session.summary?.one_line_summary && (
                    <p className="mt-3 text-sm font-semibold text-[#3d2b1f]/80">
                      {session.summary.one_line_summary}
                    </p>
                  )}

                  <div className="mt-3 pt-3 border-t border-[#faedcd]">
                    {turns.length === 0 ? (
                      <p className="text-sm font-semibold text-[#3d2b1f]/50 italic">No speech recorded.</p>
                    ) : (
                      <>
                        {!isOpen && (
                          <p className="text-sm font-semibold text-[#3d2b1f]/75 line-clamp-2 italic font-sans">
                            {lastTurn?.user || lastTurn?.text || "No speech recorded."}
                          </p>
                        )}
                        <button
                          onClick={() => setOpenSession(isOpen ? null : session.id)}
                          aria-expanded={isOpen}
                          className="mt-2 flex items-center gap-1 text-xs font-bold text-[#d4a373] hover:text-[#b5835a] cursor-pointer"
                        >
                          <ChevronDown size={14} className={isOpen ? "rotate-180 transition-transform" : "transition-transform"} />
                          {isOpen ? "Hide transcript" : `Show transcript (${turns.length} turns)`}
                        </button>
                        {isOpen && (
                          <div className="mt-3 space-y-2">
                            {turns.map((turn, index) => (
                              <div key={index} className="space-y-1">
                                {(turn.user || (turn.role === "user" && turn.text)) && (
                                  <p className="text-sm font-semibold text-[#2d1e18]">
                                    <span className="text-xs font-black uppercase tracking-wider text-[#3d2b1f]/50 mr-2">Caller</span>
                                    {turn.user || turn.text}
                                  </p>
                                )}
                                {(turn.ai || (turn.role === "assistant" && turn.text)) && (
                                  <p className="text-sm font-semibold text-[#3d2b1f]/80">
                                    <span className="text-xs font-black uppercase tracking-wider text-[#d4a373] mr-2">AI</span>
                                    {turn.ai || turn.text}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Objections */}
      {lead.objections && lead.objections.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-black text-[#2d1e18] font-display">Objections Logged</h2>
          <div className="space-y-3">
            {lead.objections?.map((objection) => (
              <div
                key={objection.id}
                className="bg-white/50 backdrop-blur-sm rounded-lg border border-[#faedcd]/60 p-5 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-bold text-[#2d1e18] capitalize font-display">
                      {objection.objectionType}
                    </p>
                    <p className="text-sm font-semibold text-[#3d2b1f]/80 mt-1">
                      {objection.objectionText}
                    </p>
                  </div>
                  <Badge
                    variant="custom"
                    customBgColor={
                      objection.resolved ? "bg-emerald-100/50" : "bg-rose-100/50"
                    }
                    customTextColor={
                      objection.resolved ? "text-emerald-800 border border-emerald-200/50" : "text-rose-800 border border-rose-200/50"
                    }
                    value={objection.resolved ? "Resolved" : "Unresolved"}
                    size="sm"
                  />
                </div>
                <p className="text-[10px] font-bold text-[#3d2b1f]/50 mt-3 uppercase tracking-wider">
                  Logged on {formatDateTime(objection.timestamp)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notes */}
      <div className="space-y-4">
        <h2 className="text-xl font-black text-[#2d1e18] font-display">Internal Notes</h2>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={5000}
          placeholder="Add internal notes about this lead..."
          className="w-full px-4 py-3 bg-white/70 border border-[#faedcd] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-[#3d2b1f] font-medium placeholder-[#3d2b1f]/30"
          rows={4}
        />
        <button
          onClick={saveNotes}
          disabled={savingNotes || notes === savedNotes}
          className="mt-2 px-6 py-2.5 bg-[#d4a373] text-white font-bold rounded-lg hover:bg-[#b5835a] transition-all cursor-pointer shadow-sm active:scale-95 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {savingNotes ? "Saving..." : "Save Notes"}
        </button>
      </div>
    </div>
  );
};

export default LeadDetailPage;
