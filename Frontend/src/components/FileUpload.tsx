/**
 * File upload component for documents and PDFs
 */

import React, { useRef } from "react";
import { Upload, AlertCircle } from "lucide-react";

interface FileUploadProps {
  onFileSelected: (file: File) => void;
  isLoading?: boolean;
  error?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelected,
  isLoading = false,
  error,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onFileSelected(file);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      onFileSelected(file);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  };

  return (
    <div>
      <div
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="border-2 border-dashed border-blue-300 rounded-lg p-8 text-center cursor-pointer hover:bg-blue-50 transition-colors"
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.doc,.docx,.txt"
          className="hidden"
          disabled={isLoading}
        />
        <Upload className="mx-auto mb-2 text-blue-600" size={32} />
        <p className="text-gray-700 font-medium">
          {isLoading ? "Uploading..." : "Drag and drop or click to upload"}
        </p>
        <p className="text-gray-500 text-sm mt-1">
          Supported formats: PDF, DOC, DOCX, TXT (Max 50MB)
        </p>
      </div>
      {error && (
        <div className="flex items-center gap-2 mt-3 text-red-600 bg-red-50 p-3 rounded-lg">
          <AlertCircle size={18} />
          <span className="text-sm">{error}</span>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
