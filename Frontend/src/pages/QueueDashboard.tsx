import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiService, QueueStatsResponse, DlqJob } from '../services/apiService';
import toast from 'react-hot-toast';
import { AlertTriangle, RefreshCw, Server, Activity, ArrowRight, XCircle, CheckCircle2 } from 'lucide-react';

const QueueDashboard: React.FC = () => {
  const [stats, setStats] = useState<QueueStatsResponse | null>(null);
  const [dlqJobs, setDlqJobs] = useState<DlqJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [statsRes, jobsRes] = await Promise.all([
        apiService.getQueueStats(),
        apiService.getDlqJobs(50) // Fetch up to 50 jobs
      ]);
      setStats(statsRes);
      setDlqJobs(jobsRes);
    } catch (error) {
      console.error('Error fetching queue data:', error);
      toast.error('Failed to load queue data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto refresh every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRetry = async (jobId: string) => {
    try {
      setIsRetrying(jobId);
      await apiService.retryDlqJob(jobId);
      toast.success('Job queued for retry');
      // Optimistically remove from list
      setDlqJobs(prev => prev.filter(job => job.id !== jobId));
      // Refresh stats
      fetchData();
    } catch (error) {
      console.error('Error retrying job:', error);
      toast.error('Failed to retry job');
    } finally {
      setIsRetrying(null);
    }
  };

  const handleRetryAll = async () => {
    for (const job of dlqJobs) {
      await handleRetry(job.id);
    }
    toast.success('All jobs queued for retry');
  };

  if (isLoading && !stats) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4 text-[#d4a373]">
          <RefreshCw className="animate-spin" size={40} />
          <p className="font-medium animate-pulse">Loading Queue Stats...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-[#2d1e18] to-[#3d2b1f] p-8 rounded-[2rem] shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <Server size={120} />
        </div>
        <div className="relative z-10 space-y-2">
          <h1 className="text-3xl font-bold text-[#faedcd] flex items-center gap-3">
            <Activity className="text-[#d4a373]" />
            Queue & Background Workers
          </h1>
          <p className="text-[#fefae0]/80">Manage background tasks and retry failed jobs.</p>
        </div>
        <div className="relative z-10 flex gap-4">
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-6 py-3 bg-[#faedcd]/10 hover:bg-[#faedcd]/20 text-[#faedcd] rounded-xl transition-all duration-300 font-medium border border-[#faedcd]/20"
          >
            <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          whileHover={{ y: -5 }}
          className="bg-white/80 backdrop-blur-xl p-6 rounded-3xl border border-[#d4a373]/30 shadow-xl flex items-center gap-6"
        >
          <div className="p-4 bg-[#fefae0] text-[#d4a373] rounded-2xl">
            <Server size={32} />
          </div>
          <div>
            <p className="text-[#3d2b1f]/60 font-semibold mb-1">Active Workers</p>
            <h3 className="text-3xl font-bold text-[#2d1e18]">{stats?.active_workers || 0}</h3>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -5 }}
          className="bg-white/80 backdrop-blur-xl p-6 rounded-3xl border border-[#d4a373]/30 shadow-xl flex items-center gap-6"
        >
          <div className="p-4 bg-blue-50 text-blue-500 rounded-2xl">
            <Activity size={32} />
          </div>
          <div>
            <p className="text-[#3d2b1f]/60 font-semibold mb-1">Pending Jobs</p>
            <h3 className="text-3xl font-bold text-[#2d1e18]">{stats?.total_pending || 0}</h3>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -5 }}
          className="bg-white/80 backdrop-blur-xl p-6 rounded-3xl border border-red-200 shadow-xl flex items-center gap-6"
        >
          <div className="p-4 bg-red-50 text-red-500 rounded-2xl">
            <AlertTriangle size={32} />
          </div>
          <div>
            <p className="text-[#3d2b1f]/60 font-semibold mb-1">Failed Jobs (DLQ)</p>
            <h3 className="text-3xl font-bold text-red-600">{stats?.dlq_size || 0}</h3>
          </div>
        </motion.div>
      </div>

      {/* DLQ Table */}
      <div className="bg-white/80 backdrop-blur-xl border border-[#d4a373]/30 rounded-3xl shadow-xl overflow-hidden flex flex-col">
        <div className="p-6 border-b border-[#d4a373]/20 flex justify-between items-center bg-[#faedcd]/30">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 text-red-500 rounded-lg">
              <AlertTriangle size={20} />
            </div>
            <h2 className="text-xl font-bold text-[#2d1e18]">Dead Letter Queue</h2>
            <span className="px-3 py-1 bg-red-100 text-red-600 text-xs font-bold rounded-full ml-2">
              {dlqJobs.length} Jobs
            </span>
          </div>
          {dlqJobs.length > 0 && (
            <button
              onClick={handleRetryAll}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#d4a373] hover:bg-[#bc8a5f] text-white rounded-xl transition-all duration-300 font-medium shadow-lg shadow-[#d4a373]/30"
            >
              <RefreshCw size={16} />
              Retry All Failed
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          {dlqJobs.length === 0 ? (
            <div className="p-12 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mb-4">
                <CheckCircle2 size={40} className="text-green-500" />
              </div>
              <h3 className="text-xl font-bold text-[#2d1e18] mb-2">Queue is Empty</h3>
              <p className="text-[#3d2b1f]/60 max-w-sm">
                There are no failed jobs in the Dead Letter Queue. Everything is running smoothly!
              </p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#fefae0]/50 text-[#3d2b1f]/70 text-sm border-b border-[#d4a373]/20">
                  <th className="p-4 font-semibold">Job ID</th>
                  <th className="p-4 font-semibold">Type</th>
                  <th className="p-4 font-semibold">Error Message</th>
                  <th className="p-4 font-semibold">Failed At</th>
                  <th className="p-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {dlqJobs.map((job) => (
                    <motion.tr
                      key={job.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="border-b border-[#d4a373]/10 hover:bg-[#faedcd]/20 transition-colors group"
                    >
                      <td className="p-4">
                        <span className="font-mono text-xs px-2 py-1 bg-[#2d1e18]/5 text-[#2d1e18]/70 rounded-md border border-[#2d1e18]/10">
                          {job.id ? job.id.substring(0, 8) + '...' : 'Unknown'}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="px-3 py-1 bg-blue-50 text-blue-600 text-xs font-semibold rounded-full border border-blue-100 uppercase tracking-wide">
                          {job.type}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-start gap-2 max-w-md">
                          <XCircle className="text-red-500 shrink-0 mt-0.5" size={16} />
                          <span className="text-sm text-red-600/90 font-medium break-words">
                            {job.error || 'Unknown error occurred'}
                          </span>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-[#3d2b1f]/70">
                        {new Date(job.updated_at || job.created_at || Date.now()).toLocaleString()}
                      </td>
                      <td className="p-4 text-right">
                        <button
                          onClick={() => handleRetry(job.id)}
                          disabled={isRetrying === job.id}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-[#d4a373] text-[#d4a373] hover:text-white border border-[#d4a373]/50 hover:border-transparent rounded-lg transition-all duration-300 font-medium shadow-sm hover:shadow-md disabled:opacity-50"
                        >
                          {isRetrying === job.id ? (
                            <RefreshCw size={16} className="animate-spin" />
                          ) : (
                            <ArrowRight size={16} />
                          )}
                          Retry
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default QueueDashboard;
