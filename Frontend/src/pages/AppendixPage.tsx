/**
 * AppendixPage - Upload and manage appendix documents for AI agent
 */

import React, { useState, useEffect } from "react";
import { FileText, Download, Trash2, Calendar, Info } from "lucide-react";
import FileUpload from "../components/FileUpload";
import { apiService } from "../services/apiService";
import type { AppendixFile } from "../utils/appendixStorage";

const AppendixPage: React.FC = () => {
  const [files, setFiles] = useState<AppendixFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const storedFiles = await apiService.listDocuments();
      setFiles(storedFiles);
    } catch (err) {
      setError("Failed to load documents from server");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelected = async (file: File) => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Validate file type
      const validTypes = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
      ];

      if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|doc|docx|txt)$/i)) {
        throw new Error("Invalid file type. Please upload PDF, DOC, DOCX, or TXT files only.");
      }

      await apiService.uploadDocument(file);
      setSuccessMessage(`Successfully uploaded and indexed: ${file.name}`);
      loadFiles(); // Refresh list

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload file");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteFile = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this document and its AI indexing?")) {
      setIsLoading(true);
      try {
        await apiService.deleteDocument(id);
        setFiles(files.filter((f) => (f as any).document_id !== id));
        setSuccessMessage("Document deleted successfully");
        setTimeout(() => setSuccessMessage(null), 3000);
        loadFiles();
      } catch (err) {
        setError("Failed to delete document from server");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleDownloadFile = (file: any) => {
    if (file.storage_url) {
      window.open(file.storage_url, "_blank");
    } else {
      alert("Download link not available for this document");
    }
  };

  const handleClearAll = () => {
    alert("Please delete documents individually for safety.");
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display">Knowledge Base Documents</h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-2">
          Upload and manage corporate reference files (PDF, Word, Text) that the AI agent uses to contextually query real business facts during calls.
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="p-4 bg-emerald-100/50 border border-emerald-200/50 rounded-2xl text-emerald-800 font-bold text-sm shadow-sm">
          {successMessage}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-rose-100/50 border border-rose-200/50 rounded-2xl text-rose-800 font-bold text-sm shadow-sm">
          {error}
        </div>
      )}

      {/* Upload Section */}
      <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40">
        <h2 className="text-xl font-black text-[#2d1e18] font-display mb-4">Upload New Resource</h2>
        <FileUpload onFileSelected={handleFileSelected} isLoading={isLoading} error={error} />
      </div>

      {/* Files List Section */}
      <div className="glass rounded-3xl border border-[#faedcd]/60 shadow-xl bg-white/40 overflow-hidden">
        <div className="p-6 border-b border-[#faedcd]/60 flex justify-between items-center bg-[#faedcd]/10">
          <h2 className="text-xl font-black text-[#2d1e18] font-display">
            Active Assets ({files.length})
          </h2>
          {files.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-4 py-2 text-sm font-bold text-rose-700 bg-rose-100/40 hover:bg-rose-100/70 border border-rose-200/40 rounded-xl transition-all cursor-pointer shadow-sm"
            >
              Clear All
            </button>
          )}
        </div>

        {files.length === 0 ? (
          <div className="p-12 text-center text-[#3d2b1f]/60 font-semibold">
            <FileText size={48} className="mx-auto mb-3 text-[#3d2b1f]/20" />
            <p className="text-base text-[#2d1e18] font-bold">No assets uploaded yet</p>
            <p className="text-sm text-[#3d2b1f]/50 mt-1">Upload documents to bootstrap the RAG knowledge bank.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#faedcd]/20 border-b border-[#faedcd]/60">
                  <th className="px-6 py-4 text-xs font-bold text-[#3d2b1f]/75 uppercase tracking-wider">File Name</th>
                  <th className="px-6 py-4 text-xs font-bold text-[#3d2b1f]/75 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-4 text-xs font-bold text-[#3d2b1f]/75 uppercase tracking-wider">Chunks Index</th>
                  <th className="px-6 py-4 text-xs font-bold text-[#3d2b1f]/75 uppercase tracking-wider">Uploaded</th>
                  <th className="px-6 py-4 text-xs font-bold text-[#3d2b1f]/75 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#faedcd]/60">
                {files.map((file: any) => (
                  <tr key={file.document_id} className="border-b border-[#faedcd]/60 hover:bg-white/35 transition-colors">
                    <td className="px-6 py-4 text-sm font-bold text-[#2d1e18]">
                      <div className="flex items-center gap-2">
                        <FileText size={18} className="text-[#d4a373]" />
                        <span className="truncate max-w-xs">{file.file_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-[#3d2b1f]/70 uppercase text-xs">{file.document_type || "N/A"}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-[#3d2b1f]/70">
                      {file.chunk_count} chunks indexed
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-[#3d2b1f]/70">
                      <div className="flex items-center gap-1.5">
                        <Calendar size={14} className="text-[#d4a373]" />
                        {formatDate(file.uploaded_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleDownloadFile(file)}
                          className="p-2 text-[#d4a373] hover:bg-[#faedcd]/50 rounded-xl border border-[#d4a373]/15 transition-all cursor-pointer shadow-sm"
                          title="View"
                        >
                          <Download size={16} />
                        </button>
                        <button
                          onClick={() => handleDeleteFile(file.document_id)}
                          className="p-2 text-rose-600 hover:bg-rose-100/50 rounded-xl border border-rose-200/20 transition-all cursor-pointer shadow-sm"
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="mt-8 p-6 bg-[#faedcd]/20 border border-[#faedcd] rounded-3xl shadow-sm flex gap-3">
        <Info size={24} className="text-[#d4a373] shrink-0 mt-0.5" />
        <div>
          <h3 className="font-black text-[#2d1e18] mb-1.5 font-display">How indexing works</h3>
          <ul className="text-sm text-[#3d2b1f]/80 font-semibold space-y-1.5 list-disc list-inside">
            <li>Upload company details, service brochures, or FAQs.</li>
            <li>Uploaded assets get split into vector chunks instantly.</li>
            <li>Our AI agent semantic-searches these indexed files to answer client questions in real-time.</li>
            <li>Removing documents immediately cleanses them from the active AI knowledge pool.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default AppendixPage;
