"use client";

import { useSession, signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // If already logged in, send them to the dashboard
  useEffect(() => {
    if (status === "authenticated") {
      router.push("/dashboard");
    }
  }, [status, router]);

  // While checking auth status, show nothing (prevents flash of landing page)
  if (status === "loading" || status === "authenticated") {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b px-6 py-4 flex justify-between items-center max-w-6xl mx-auto">
        <h1 className="text-xl font-bold text-blue-700">ClinIQ</h1>
        <button
          onClick={() => signIn("google")}
          className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
        >
          Sign in with Google
        </button>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-5xl font-bold text-gray-900 mb-6">
          Ask your clinical documents anything
        </h2>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          Upload clinical trial protocols, SAPs, or regulatory documents. Ask
          questions in plain English. Get AI-powered answers with exact page
          and section references.
        </p>
        <button
          onClick={() => signIn("google")}
          className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg hover:bg-blue-700 transition"
        >
          Sign in to Get Started →
        </button>
      </section>

      {/* How It Works */}
      <section className="bg-gray-50 py-16">
        <div className="max-w-5xl mx-auto px-6">
          <h3 className="text-2xl font-bold text-center mb-12">
            How It Works
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="text-3xl mb-4">📄</div>
              <h4 className="font-semibold text-lg mb-2">1. Upload</h4>
              <p className="text-gray-600">
                Drop your clinical trial protocol or regulatory document (PDF)
              </p>
            </div>
            <div className="text-center p-6">
              <div className="text-3xl mb-4">💬</div>
              <h4 className="font-semibold text-lg mb-2">2. Ask</h4>
              <p className="text-gray-600">
                Type your question in plain English — like asking a colleague
              </p>
            </div>
            <div className="text-center p-6">
              <div className="text-3xl mb-4">🎯</div>
              <h4 className="font-semibold text-lg mb-2">
                3. Get Cited Answers
              </h4>
              <p className="text-gray-600">
                AI-powered answers with exact page numbers and section
                references
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Built For */}
      <section className="py-16">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h3 className="text-2xl font-bold mb-8">
            Built for Pharma Professionals
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-gray-600">
            <div className="p-4 bg-gray-50 rounded-lg">Medical Writers</div>
            <div className="p-4 bg-gray-50 rounded-lg">Clinical Scientists</div>
            <div className="p-4 bg-gray-50 rounded-lg">Biostatisticians</div>
            <div className="p-4 bg-gray-50 rounded-lg">Regulatory Affairs</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 text-center text-gray-500 text-sm">
        ClinIQ — Built by Gaurav Gupta | Pharma AI & Clinical Operations
      </footer>
    </main>
  );
}
