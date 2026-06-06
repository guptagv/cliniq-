"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";

interface DocInfo {
  name: string;
  display_name: string;
  chunks: number;
}

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    }
  }, [status, router]);

  useEffect(() => {
    const fetchDocs = async () => {
      if (!session?.user?.email) return;
      try {
        const res = await fetch(
          `${API_URL}/documents?user_id=${session.user.email}`
        );
        const data = await res.json();
        setDocuments(data.documents || []);
      } catch {
        setDocuments([]);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [session, API_URL]);

  if (status === "loading" || !session) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Welcome, {session.user?.name?.split(" ")[0]}
            </h2>
            <p className="text-gray-500 mt-1">
              {documents.length} document{documents.length !== 1 ? "s" : ""} uploaded
            </p>
          </div>
          <a
            href="/upload"
            className="bg-blue-600 text-white px-5 py-2.5 rounded-lg hover:bg-blue-700 transition text-sm"
          >
            Upload New Document
          </a>
        </div>

        {loading ? (
          <p className="text-gray-400">Loading documents...</p>
        ) : documents.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-500 text-lg mb-4">No documents uploaded yet</p>
            <p className="text-gray-400 mb-6">
              Upload a clinical trial protocol to get started
            </p>
            <a
              href="/upload"
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
            >
              Upload Your First Document
            </a>
          </div>
        ) : (
          <div className="grid gap-4">
            {documents.map((doc) => (
              <div
                key={doc.name}
                className="bg-white rounded-xl border border-gray-200 p-6 flex justify-between items-center hover:border-blue-300 transition"
              >
                <div>
                  <h3 className="font-medium text-gray-900">
                    {doc.display_name}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {doc.chunks} searchable chunks
                  </p>
                </div>
                <button
                  onClick={() => router.push(`/chat?doc=${doc.name}`)}
                  className="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg hover:bg-blue-100 transition text-sm"
                >
                  Chat with this document →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}