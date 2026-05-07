/**
 * AppendixPage - Upload and manage appendix documents for AI agent
 */

import React, { useState, useEffect } from "react";
import { FileText, Download, Trash2, Calendar } from "lucide-react";
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
    // Backend doesn't have a direct download endpoint in the router we saw,
    // but typically it would be a link to storage
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
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Appendix Documents</h1>
        <p className="text-gray-600 mt-2">
          Upload and manage documents (PDF, Word, Text) that the AI agent will use to understand
          your business details when speaking with clients
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
          {successMessage}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-900">Upload New Document</h2>
        <FileUpload onFileSelected={handleFileSelected} isLoading={isLoading} error={error} />
      </div>

      {/* Files List Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Uploaded Documents ({files.length})
          </h2>
          {files.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              Clear All
            </button>
          )}
        </div>

        {files.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <FileText size={48} className="mx-auto mb-3 text-gray-300" />
            <p>No documents uploaded yet</p>
            <p className="text-sm mt-2">Upload documents to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    File Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Uploaded
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {files.map((file: any) => (
                  <tr key={file.document_id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      <div className="flex items-center gap-2">
                        <FileText size={18} className="text-blue-600" />
                        <span className="truncate max-w-xs">{file.file_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{file.document_type || "N/A"}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {file.chunk_count} chunks
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      <div className="flex items-center gap-1">
                        <Calendar size={14} className="text-gray-400" />
                        {formatDate(file.uploaded_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDownloadFile(file)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                          title="View"
                        >
                          <Download size={18} />
                        </button>
                        <button
                          onClick={() => handleDeleteFile(file.document_id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={18} />
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
      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">ℹ️ How it works</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>Upload company details, service descriptions, or any relevant documents</li>
          <li>These documents are stored locally and will be used by the AI agent</li>
          <li>The agent references this information when speaking with clients</li>
          <li>You can update or remove documents at any time</li>
        </ul>
      </div>
    </div>
  );
};

export default AppendixPage;
