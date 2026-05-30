"use client";

   import { useState } from "react";
   import { useRouter } from "next/navigation";

   export default function UploadPage() {
     const [file, setFile] = useState<File | null>(null);
     const [uploading, setUploading] = useState(false);
     const [result, setResult] = useState<any>(null);
     const [error, setError] = useState<string>("");
     const router = useRouter();

     const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
           throw new Error("Upload failed. Please try again.");
         }

         const data = await response.json();
         setResult(data);
       } catch (err: any) {
         setError(err.message || "Something went wrong");
       } finally {
         setUploading(false);
       }
     };

     return (
       <main className="min-h-screen bg-gray-50">
         <nav className="border-b bg-white px-6 py-4">
           <a href="/" className="text-xl font-bold text-blue-700">ClinIQ</a>
         </nav>

         <div className="max-w-2xl mx-auto px-6 py-16">
           <h2 className="text-3xl font-bold mb-2">Upload Document</h2>
           <p className="text-gray-600 mb-8">
             Upload a clinical trial protocol or regulatory document (PDF, max 10MB)
           </p>

           {/* Upload Area */}
           {/* Upload Area */}
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center bg-white">
            <p className="text-gray-500 mb-4">Select a clinical trial protocol (PDF)</p>
            <label className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 cursor-pointer transition">
                Choose PDF File
                <input
                type="file"
                accept=".pdf"
                onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setResult(null);
                    setError("");
                }}
                className="hidden"
                />
            </label>
             {file && (
               <div className="mt-4">
                 <p className="text-sm text-gray-600 mb-4">
                   Selected: <span className="font-medium">{file.name}</span>{" "}
                   ({(file.size / 1024 / 1024).toFixed(1)} MB)
                 </p>

                 <button
                   onClick={handleUpload}
                   disabled={uploading}
                   className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition"
                 >
                   {uploading ? "Processing... (this may take a minute)" : "Upload & Process"}
                 </button>
               </div>
             )}
           </div>

           {/* Error */}
           {error && (
             <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-lg">
               {error}
             </div>
           )}

           {/* Success */}
           {result && (
             <div className="mt-6 p-6 bg-green-50 rounded-lg">
               <h3 className="font-semibold text-green-800 mb-2">Document Processed!</h3>
               <p className="text-green-700">
                 {result.pages} pages extracted, {result.chunks} searchable chunks created.
               </p>
               <button
                 onClick={() => router.push("/chat")}
                 className="mt-4 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition"
               >
                 Start Asking Questions →
               </button>
             </div>
           )}
         </div>
       </main>
     );
   }