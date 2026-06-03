"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  pages?: number[];
  sections?: string[];
  confidence?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hasDocuments, setHasDocuments] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Check if any documents are uploaded
  useEffect(() => {
    const checkDocuments = async () => {
      try {
        const res = await fetch(`${API_URL}/health`);
        const data = await res.json();
        setHasDocuments(data.documents_loaded > 0);
      } catch {
        setHasDocuments(false);
      }
    };
    checkDocuments();
  }, [API_URL]);

  // Auto-scroll to bottom when new messages appear
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (overrideQuestion?: string) => {
    const question = overrideQuestion || input.trim();
    if (!question || loading) return;

    setInput("");

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) throw new Error("Failed to get answer");

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          pages: data.pages_cited,
          sections: data.sections_cited,
          confidence: data.confidence,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, something went wrong. Make sure the backend is running and try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const starterQuestions = [
    "What is the primary endpoint?",
    "List the inclusion criteria",
    "How is the study drug administered?",
    "What adverse events are monitored?",
    "What is the sample size?",
  ];

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col">
      {/* Nav */}
      <nav className="border-b bg-white px-6 py-4 flex justify-between items-center">
        <a href="/" className="text-xl font-bold text-blue-700">ClinIQ</a>
        <a href="/upload" className="text-sm text-blue-600 hover:underline">
          Upload New Document
        </a>
      </nav>

      {/* No Documents Warning */}
      {hasDocuments === false && (
        <div className="max-w-3xl mx-auto w-full px-6 mt-8">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800 font-medium mb-1">No documents uploaded yet</p>
            <p className="text-yellow-700 text-sm">
              You need to upload a clinical trial document before asking questions.{" "}
              <a href="/upload" className="underline font-medium">
                Upload a document →
              </a>
            </p>
          </div>
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8 max-w-3xl mx-auto w-full">
        {/* Starter questions when no messages */}
        {messages.length === 0 && hasDocuments !== false && (
          <div className="text-center mt-20">
            <p className="text-lg text-gray-400 mb-2">
              Ask a question about your document
            </p>
            <p className="text-sm text-gray-400 mb-6">Or try one of these:</p>
            <div className="flex flex-wrap justify-center gap-3">
              {starterQuestions.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition text-sm"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`mb-6 ${msg.role === "user" ? "text-right" : ""}`}
          >
            <div
              className={`inline-block max-w-[85%] p-4 rounded-xl ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>

            {/* Citation badges */}
            {msg.role === "assistant" && msg.pages && msg.pages.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {msg.pages.map((p) => (
                  <span
                    key={p}
                    className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                  >
                    Page {p}
                  </span>
                ))}
                {msg.sections?.map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded"
                  >
                    {s}
                  </span>
                ))}
                {msg.confidence && (
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      msg.confidence === "high"
                        ? "bg-green-100 text-green-700"
                        : msg.confidence === "medium"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {msg.confidence} confidence
                  </span>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="mb-6">
            <div className="inline-block bg-white border border-gray-200 p-4 rounded-xl rounded-bl-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                <div
                  className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                />
                <div
                  className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
                <p className="text-gray-400 ml-2">
                  Searching document and generating answer...
                </p>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Bar */}
      <div className="border-t bg-white px-6 py-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask a question about your document..."
            disabled={hasDocuments === false}
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim() || hasDocuments === false}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition"
          >
            Ask
          </button>
        </div>
      </div>
    </main>
  );
}