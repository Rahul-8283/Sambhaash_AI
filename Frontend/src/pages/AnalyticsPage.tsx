import React, { useState, useEffect } from "react";
import { apiService } from "../services/apiService";
import MetricCard from "../components/MetricCard";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { BookOpen, PhoneCall, CheckCircle, Target } from "lucide-react";

export const AnalyticsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        const kbMetrics = await apiService.getKBEffectiveness(30);
        setMetrics(kbMetrics);
      } catch (error) {
        console.error("Failed to load analytics:", error);
      } finally {
        setLoading(false);
      }
    };
    loadAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-center text-[#3d2b1f]/60 font-bold flex flex-col items-center justify-center min-h-[300px]">
        <p className="animate-pulse">Loading business insights...</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-8 text-center text-[#3d2b1f]/60 font-bold min-h-[300px] flex items-center justify-center">
        No analytics data available
      </div>
    );
  }

  // Earth-sand themed chart color steps
  const COLORS = ['#d4a373', '#b5835a', '#faedcd', '#e6ccb2', '#9c6644'];

  return (
    <div className="p-6 pt-2 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display">System Analytics</h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-1">AI Performance and Knowledge Base Effectiveness</p>
      </div>

      {/* High Level Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <MetricCard
          label="Total Calls"
          value={metrics.total_calls_analyzed}
          icon={<PhoneCall className="text-[#d4a373]" size={20} />}
        />
        <MetricCard
          label="Calls with AI Help"
          value={metrics.calls_with_kb_usage}
          icon={<BookOpen className="text-[#d4a373]" size={20} />}
        />
        <MetricCard
          label="Avg Queries / Call"
          value={metrics.avg_documents_per_call.toFixed(1)}
          icon={<Target className="text-[#d4a373]" size={20} />}
        />
        <MetricCard
          label="AI Knowledge Coverage"
          value={`${metrics.kb_coverage_percentage.toFixed(1)}%`}
          icon={<CheckCircle className="text-[#d4a373]" size={20} />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Most Used Knowledge Documents */}
        <div className="glass rounded-lg p-6 border border-[#faedcd]/60 shadow-xl bg-white/40">
          <h2 className="text-xl font-black text-[#2d1e18] font-display mb-6">Top Knowledge Assets</h2>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.most_used_documents} layout="vertical" margin={{ left: 10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#faedcd" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#3d2b1f', fontSize: 10, fontWeight: '600' }} />
                <YAxis 
                  type="category" 
                  dataKey="document_name" 
                  width={110} 
                  tick={{ fill: '#3d2b1f', fontSize: 9, fontWeight: '700' }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                    borderRadius: '16px', 
                    border: '1px solid #faedcd',
                    boxShadow: '0 10px 25px -5px rgba(0,0,0,0.05)',
                    fontWeight: 'bold',
                    color: '#3d2b1f'
                  }} 
                />
                <Bar dataKey="usage_count" radius={[0, 8, 8, 0]}>
                  {metrics.most_used_documents.map((_entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Relevance Scores */}
        <div className="glass rounded-lg p-6 border border-[#faedcd]/60 shadow-xl flex flex-col justify-center items-center text-center bg-white/40">
          <h2 className="text-xl font-black text-[#2d1e18] font-display mb-2">AI Response Accuracy</h2>
          <div className="text-6xl font-black text-[#d4a373] mb-4 font-display tracking-tight">
            {(metrics.avg_relevance_score * 100).toFixed(0)}%
          </div>
          <p className="text-[#3d2b1f]/70 font-semibold max-w-xs text-sm">
            Average confidence score of AI-retrieved knowledge across all customer interactions.
          </p>
          <div className="mt-8 w-full bg-[#faedcd]/50 rounded-lg h-4 overflow-hidden border border-[#faedcd]/60">
            <div 
              className="bg-[#d4a373] h-full transition-all duration-1000 rounded-lg" 
              style={{ width: `${metrics.avg_relevance_score * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;