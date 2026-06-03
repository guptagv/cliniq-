"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const validateFile = (selectedFile: File): string | null => {
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      return "Only PDF files are supported. Please select a .pdf file.";
    }
    if (selectedFile.size > MAX_FILE_SIZE) {
      return `File is too large (${(selectedFile.size / 1024 / 1024).toFixed(1)}MB). Maximum size is 10MB.`;
    }
    if (selectedFile.size === 0) {
      return "This file appears to be empty. Please select a valid PDF.";
    }
    return null;
  };

  const handleFileSelect = (selectedFile: File | null) => {
    setResult(null);
    setError("");

    if (!selectedFile) {
      setFile(null);
      return;
    }

    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `Upload failed (status ${response.status}). Please try again.`
        );
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      if (err.message === "Failed to fetch") {
        setError(
          "Cannot connect to the backend server. Make sure the backend is running on " + API_URL
        );
      } else {
        setError(err.message || "Something went wrong. Please try again.");
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <nav className="border-b bg-white px-6 py-4 flex justify-between items-center">
        <a href="/" className="text-xl font-bold text-blue-700">ClinIQ</a>
        <a href="/chat" className="text-sm text-blue-600 hover:underline">
          Go to Chat
        </a>
      </nav>

      <div className="max-w-2xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold mb-2">Upload Document</h2>
        <p className="text-gray-600 mb-8">
          Upload a clinical trial protocol or regulatory document (PDF, max 10MB)
        </p>

        {/* Drop Zone */}
        <div
          className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center bg-white hover:border-blue-400 transition"
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.classList.add("border-blue-400", "bg-blue-50");
          }}
          onDragLeave={(e) => {
            e.currentTarget.classList.remove("border-blue-400", "bg-blue-50");
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.currentTarget.classList.remove("border-blue-400", "bg-blue-50");
            const droppedFile = e.dataTransfer.files[0];
            handleFileSelect(droppedFile || null);
          }}
        >
          <p className="text-gray-500 mb-4">
            Drag and drop your PDF here, or
          </p>
          <label className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 cursor-pointer transition">
            Choose PDF File
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
              className="hidden"
            />
          </label>

          {file && (
            <div className="mt-6">
              <p className="text-sm text-gray-600 mb-4">
                Selected: <span className="font-medium">{file.name}</span>{" "}
                ({(file.size / 1024 / 1024).toFixed(1)} MB)
              </p>

              <button
                onClick={handleUpload}
                disabled={uploading}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition"
              >
                {uploading
                  ? "Processing... (this may take a minute)"
                  : "Upload & Process"}
              </button>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            <p className="font-medium mb-1">Error</p>
            <p>{error}</p>
          </div>
        )}

        {/* Success */}
        {result && (
          <div className="mt-6 p-6 bg-green-50 border border-green-200 rounded-lg">
            <h3 className="font-semibold text-green-800 mb-2">
              Document Processed Successfully!
            </h3>
            <p className="text-green-700 mb-1">
              {result.pages} pages extracted, {result.chunks} searchable chunks created.
            </p>
            {result.collection_name && (
              <p className="text-green-600 text-sm mb-4">
                Document ID: {result.collection_name}
              </p>
            )}
            <button
              onClick={() => router.push("/chat")}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition"
            >
              Start Asking Questions →
            </button>
          </div>
        )}
      </div>
    </main>
  );
}