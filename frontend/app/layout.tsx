import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "ClinIQ — AI-Powered Clinical Document Q&A",
  description:
    "Upload clinical trial protocols, ask questions in plain English, get AI-powered answers with page citations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}