/**
 * Lead detail page - shows single lead with call history, scores, and actions
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Phone, Mail } from "lucide-react";
import mockApiClient from "../services/mockApiClient";
import type { LeadWithDetails } from "../types";
import Badge from "../components/Badge";
import { formatDateTime, formatPhoneNumber, formatDuration } from "../utils/formatters";
import MetricCard from "../components/MetricCard";

export const LeadDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [lead, setLead] = useState<LeadWithDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadLead = async () => {
      if (!id) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const result = await mockApiClient.getLeadById(id);
        setLead(result);
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

  const latestScore = lead.scoreHistory[0] || lead.currentScore;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <button
          onClick={() => navigate("/dashboard/leads")}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-4"
        >
          <ArrowLeft size={20} />
          Back to Leads
        </button>
      </div>

      {/* Lead Info Card */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{lead.name}</h1>
            <p className="text-gray-600 mt-1">Lead ID: {lead.id}</p>
          </div>
          <Badge variant="status" value={lead.status} size="lg" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 pt-6 border-t border-gray-200">
          {/* Contact Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Phone size={20} className="text-gray-400" />
              <div>
                <p className="text-sm text-gray-600">Phone</p>
                <p className="font-medium">{formatPhoneNumber(lead.phone)}</p>
              </div>
            </div>
            {lead.email && (
              <div className="flex items-center gap-3">
                <Mail size={20} className="text-gray-400" />
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="font-medium">{lead.email}</p>
                </div>
              </div>
            )}
          </div>

          {/* Meta Info */}
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-600">Language</p>
              <p className="font-medium">{lead.language}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Created</p>
              <p className="font-medium">{formatDateTime(lead.createdAt)}</p>
            </div>
          </div>
        </div>

        {/* RM Assignment */}
        {lead.rmAssignment && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-2">Assigned to</p>
            <p className="font-medium">{lead.rmAssignment.rmName}</p>
            {lead.rmAssignment.converted && (
              <Badge variant="custom" customBgColor="bg-green-100" customTextColor="text-green-800" value="Converted" size="sm" />
            )}
          </div>
        )}
      </div>

      {/* Scoring Metrics */}
      {latestScore && (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Lead Score</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard
              label="Overall Score"
              value={latestScore.compositeScore.toFixed(1)}
              size="md"
            />
            <MetricCard
              label="Interest Score"
              value={latestScore.interestScore.toFixed(1)}
              size="md"
            />
            <MetricCard
              label="Engagement Score"
              value={latestScore.engagementScore.toFixed(1)}
              size="md"
            />
            <MetricCard
              label="Sentiment Score"
              value={latestScore.sentimentScore.toFixed(2)}
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
          <h2 className="text-xl font-bold text-gray-900">Call History</h2>
          <button
            onClick={() => {
              if (lead.phone) {
                window.location.href = `tel:${lead.phone}`;
              }
            }}
            disabled={!lead.phone}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Phone size={20} />
            Call Now
          </button>
        </div>

        {lead.callSessions.length === 0 ? (
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center text-gray-500">
            No calls yet
          </div>
        ) : (
          <div className="space-y-3">
            {lead.callSessions.map((session) => (
              <div
                key={session.id}
                className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {formatDuration(session.durationSeconds)}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      {formatDateTime(session.createdAt)}
                    </p>
                    {session.languageDetected && (
                      <p className="text-sm text-gray-500 mt-1">
                        Detected: {session.languageDetected}
                      </p>
                    )}
                  </div>
                  {lead?.currentScore?.classification && (
                    <Badge
                      variant="custom"
                      customBgColor={
                        lead.currentScore.classification === "Hot"
                          ? "bg-red-100"
                          : lead.currentScore.classification === "Warm"
                            ? "bg-yellow-100"
                            : lead.currentScore.classification === "Cold"
                              ? "bg-blue-100"
                              : "bg-gray-100"
                      }
                      customTextColor={
                        lead.currentScore.classification === "Hot"
                          ? "text-red-800"
                          : lead.currentScore.classification === "Warm"
                            ? "text-yellow-800"
                            : lead.currentScore.classification === "Cold"
                              ? "text-blue-800"
                              : "text-gray-800"
                      }
                      value={lead.currentScore.classification}
                      size="sm"
                    />
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {session.conversationHistory[session.conversationHistory.length - 1]?.text}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Objections */}
      {lead.objections.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Objections Logged</h2>
          <div className="space-y-3">
            {lead.objections.map((objection) => (
              <div
                key={objection.id}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 capitalize">
                      {objection.objectionType}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      {objection.objectionText}
                    </p>
                  </div>
                  <Badge
                    variant="custom"
                    customBgColor={
                      objection.resolved ? "bg-green-100" : "bg-red-100"
                    }
                    customTextColor={
                      objection.resolved ? "text-green-800" : "text-red-800"
                    }
                    value={objection.resolved ? "Resolved" : "Unresolved"}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  {formatDateTime(objection.timestamp)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notes */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-4">Notes</h2>
        <textarea
          placeholder="Add internal notes about this lead..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={4}
        />
        <button className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Save Notes
        </button>
      </div>
    </div>
  );
};

export default LeadDetailPage;
