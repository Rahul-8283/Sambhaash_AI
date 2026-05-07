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
    return <div className="p-8 text-center text-gray-500">Loading business insights...</div>;
  }

  if (!metrics) {
    return <div className="p-8 text-center text-gray-500">No analytics data available</div>;
  }

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600 mt-2">AI Performance and Knowledge Base Effectiveness</p>
      </div>

      {/* High Level Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <MetricCard
          label="Total Calls"
          value={metrics.total_calls_analyzed}
          icon={<PhoneCall className="text-blue-600" />}
        />
        <MetricCard
          label="Calls with AI Help"
          value={metrics.calls_with_kb_usage}
          icon={<BookOpen className="text-green-600" />}
        />
        <MetricCard
          label="Avg Queries / Call"
          value={metrics.avg_documents_per_call.toFixed(1)}
          icon={<Target className="text-purple-600" />}
        />
        <MetricCard
          label="AI Knowledge Coverage"
          value={`${metrics.kb_coverage_percentage.toFixed(1)}%`}
          icon={<CheckCircle className="text-amber-600" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Most Used Knowledge Documents */}
        <div className="glass rounded-3xl p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Top Knowledge Assets</h2>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.most_used_documents} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis type="category" dataKey="document_name" width={100} />
                <Tooltip />
                <Bar dataKey="usage_count" radius={[0, 4, 4, 0]}>
                  {metrics.most_used_documents.map((_entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Relevance Scores */}
        <div className="glass rounded-3xl p-6 flex flex-col justify-center items-center text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">AI Response Accuracy</h2>
          <div className="text-6xl font-black text-blue-600 mb-4">
            {(metrics.avg_relevance_score * 100).toFixed(0)}%
          </div>
          <p className="text-gray-600 max-w-xs">
            Average confidence score of AI-retrieved knowledge across all customer interactions.
          </p>
          <div className="mt-8 w-full bg-gray-100 rounded-full h-4 overflow-hidden">
            <div 
              className="bg-blue-600 h-full transition-all duration-1000" 
              style={{ width: `${metrics.avg_relevance_score * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;