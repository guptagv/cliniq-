"use client";

import { useSession, signIn, signOut } from "next-auth/react";

export default function Navbar() {
  const { data: session, status } = useSession();

  return (
    <nav className="border-b bg-white px-6 py-4 flex justify-between items-center">
      <a href="/" className="text-xl font-bold text-blue-700">
        ClinIQ
      </a>

      <div className="flex items-center gap-4">
        {status === "loading" ? (
          <span className="text-sm text-gray-400">Loading...</span>
        ) : session ? (
          <>
            <a
              href="/dashboard"
              className="text-sm text-blue-600 hover:underline"
            >
              Dashboard
            </a>
            <a
              href="/upload"
              className="text-sm text-blue-600 hover:underline"
            >
              Upload
            </a>
            <a
              href="/chat"
              className="text-sm text-blue-600 hover:underline"
            >
              Chat
            </a>
            <span className="text-sm text-gray-600">
              {session.user?.name}
            </span>
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </>
        ) : (
          <button
            onClick={() => signIn("google")}
            className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Sign in with Google
          </button>
        )}
      </div>
    </nav>
  );
}
