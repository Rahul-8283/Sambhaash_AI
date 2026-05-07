/**
 * Local storage utilities for appendix files
 */

export type AppendixFile = {
  id: string;
  name: string;
  file: string;
  type: string;
  uploadedAt: string;
  size: number;
};

const STORAGE_KEY = "sambhaash_appendix_files";
const MAX_FILE_SIZE = 50 * 1024 * 1024;

// Upload a file to local storage
export function uploadFile(file: File): Promise<AppendixFile> {
  return new Promise((resolve, reject) => {
    if (file.size > MAX_FILE_SIZE) {
      reject(new Error(`File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`));
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const appendixFile: AppendixFile = {
        id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        name: file.name,
        file: reader.result as string,
        type: file.type,
        uploadedAt: new Date().toISOString(),
        size: file.size,
      };
      resolve(appendixFile);
    };
    reader.onerror = () => {
      reject(new Error("Failed to read file"));
    };
    reader.readAsDataURL(file);
  });
}

// Save file to local storage
export function saveFile(appendixFile: AppendixFile): void {
  const files = getAllFiles();
  files.push(appendixFile);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(files));
}

// Get all files from local storage
export function getAllFiles(): AppendixFile[] {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : [];
}

// Get a specific file by ID
export function getFileById(id: string): AppendixFile | null {
  const files = getAllFiles();
  return files.find((f) => f.id === id) || null;
}

// Delete a file from local storage
export function deleteFile(id: string): void {
  const files = getAllFiles();
  const filtered = files.filter((f) => f.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
}

// Download a file
export function downloadFile(appendixFile: AppendixFile): void {
  const link = document.createElement("a");
  link.href = appendixFile.file;
  link.download = appendixFile.name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Clear all files
export function clearAll(): void {
  localStorage.removeItem(STORAGE_KEY);
}
