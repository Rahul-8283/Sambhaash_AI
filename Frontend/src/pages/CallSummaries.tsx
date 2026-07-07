import React, { useState, useEffect } from "react";
import { PhoneCall, Calendar, Clock, AlertCircle } from "lucide-react";
import { apiService } from "../services/apiService";
import { formatDateTime } from "../utils/formatters";

export const CallSummaries: React.FC = () => {
  const [summaries, setSummaries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummaries = async () => {
      try {
        const result = await apiService.getSummaries();
        setSummaries(result.data);
      } catch (error) {
        console.error("Failed to fetch summaries:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSummaries();
  }, []);

  return (
    <div className="p-4 md:p-6 pt-2 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-black text-[#2d1e18] font-display">Call Summaries</h1>
          <p className="text-sm font-semibold text-[#3d2b1f]/70">AI-generated insights from phone conversations</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-white/80 backdrop-blur-xl border border-white/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl p-4 md:p-6">
        {loading ? (
          <div className="p-12 flex justify-center text-[#d4a373] animate-pulse font-medium">Loading Summaries...</div>
        ) : summaries.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center text-center">
            <PhoneCall size={40} className="text-[#d4a373] mb-4 opacity-50" />
            <h3 className="text-xl font-bold text-[#2d1e18] mb-2">No Call Summaries Yet</h3>
            <p className="text-[#3d2b1f]/60 max-w-sm">
              Your call summaries will appear here once AI generates them from your calls.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {summaries.map((item) => (
              <div key={item.session_id} className="bg-white border border-gray-100 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
                <div className="p-5 border-b border-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-lg text-gray-900">{item.lead_name || "Unknown Lead"}</h3>
                    <span className={`px-2 py-1 text-xs font-bold rounded-full ${
                      item.classification === "HOT" ? "bg-red-100 text-red-700" :
                      item.classification === "WARM" ? "bg-orange-100 text-orange-700" :
                      item.classification === "COLD" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"
                    }`}>
                      {item.classification || "UNSCORED"}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 font-medium">{item.lead_phone}</p>
                </div>
                
                <div className="p-5 flex-1 bg-gray-50/50 space-y-4">
                  {item.summary?.one_line_summary && (
                    <p className="text-sm font-semibold italic text-gray-700 border-l-4 border-orange-400 pl-3 py-1">
                      "{item.summary.one_line_summary}"
                    </p>
                  )}
                  
                  {item.summary?.topics_covered?.length > 0 && (
                    <div>
                      <h4 className="text-xs uppercase tracking-wider font-bold text-gray-400 mb-2">Topics Covered</h4>
                      <div className="flex flex-wrap gap-2">
                        {item.summary.topics_covered.map((topic: string, i: number) => (
                          <span key={i} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-md">{topic}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {item.summary?.objections_raised?.length > 0 && (
                    <div>
                      <h4 className="text-xs uppercase tracking-wider font-bold text-gray-400 mb-2 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" /> Objections
                      </h4>
                      <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                        {item.summary.objections_raised.map((obj: string, i: number) => (
                          <li key={i}>{obj}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="p-4 border-t border-gray-50 bg-white flex justify-between items-center text-xs text-gray-400 font-medium">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {item.created_at ? formatDateTime(item.created_at) : "Unknown date"}
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {item.duration_seconds}s
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CallSummaries;
