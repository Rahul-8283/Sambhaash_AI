import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import type { RecordingMetadata } from '../services/apiService';
import { PhoneCall, Clock } from 'lucide-react';

const CallsPage: React.FC = () => {
  const [recordings, setRecordings] = useState<RecordingMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchRecordings = async () => {
    try {
      setIsLoading(true);
      const res = await apiService.getRecordings(page, 20);
      setRecordings(res.recordings);
      setTotal(res.total);
    } catch (error) {
      console.error('Failed to load recordings', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecordings();
  }, [page]);

  const formatDuration = (seconds: number) => {
    if (!seconds) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="p-4 md:p-6 pt-2 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-black text-[#2d1e18] font-display flex items-center gap-2">
            Call Logs & Recordings
          </h1>
          <p className="text-sm font-semibold text-[#3d2b1f]/70">Listen to past calls and review conversation sentiment ({total} total)</p>
        </div>
      </div>

      {/* Table */}
      <div className="glass rounded-lg border border-[#faedcd]/60 overflow-hidden flex flex-col shadow-sm">
        {isLoading ? (
           <div className="p-12 flex justify-center text-[#d4a373] animate-pulse font-medium">Loading Recordings...</div>
        ) : recordings.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center text-center">
            <PhoneCall size={40} className="text-[#d4a373] mb-4 opacity-50" />
            <h3 className="text-xl font-bold text-[#2d1e18] mb-2">No Calls Yet</h3>
            <p className="text-[#3d2b1f]/60 max-w-sm">
              Your call recordings will appear here once you start making phone calls.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#fefae0]/50 text-[#3d2b1f]/70 text-sm border-b border-[#faedcd]/80">
                  <th className="p-4 font-semibold w-16">Play Audio</th>
                  <th className="p-4 font-semibold">Date</th>
                  <th className="p-4 font-semibold">Duration</th>
                  <th className="p-4 font-semibold">Sentiment</th>
                  <th className="p-4 font-semibold">Language</th>
                  <th className="p-4 font-semibold">Topics</th>
                </tr>
              </thead>
              <tbody>
                {recordings.map((rec) => (
                  <tr key={rec.id} className="border-b border-[#faedcd]/40 hover:bg-[#faedcd]/10 transition-colors group">
                    <td className="p-4">
                      {rec.storage_url ? (
                        <audio controls src={rec.storage_url} className="w-48 h-8 rounded" preload="none" />
                      ) : (
                        <span className="text-xs text-gray-400 font-medium">No Audio</span>
                      )}
                    </td>
                    <td className="p-4 text-sm text-[#3d2b1f]/70 whitespace-nowrap">
                      {new Date(rec.created_at).toLocaleString()}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-1.5 text-sm font-medium text-[#2d1e18]">
                        <Clock size={14} className="text-[#d4a373]" />
                        {formatDuration(rec.duration_seconds)}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide
                        ${rec.sentiment === 'positive' ? 'bg-green-100 text-green-700' : 
                          rec.sentiment === 'negative' ? 'bg-red-100 text-red-700' : 
                          'bg-gray-100 text-gray-700'}`}
                      >
                        {rec.sentiment || 'Neutral'}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs font-semibold uppercase">
                        {rec.language || 'EN'}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap gap-1">
                        {rec.key_topics && rec.key_topics.length > 0 ? (
                          rec.key_topics.slice(0, 3).map((topic, i) => (
                            <span key={i} className="text-xs px-2 py-0.5 bg-[#fefae0] border border-[#d4a373]/30 text-[#d4a373] rounded-full">
                              {topic}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400">-</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default CallsPage;