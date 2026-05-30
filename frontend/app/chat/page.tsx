"use client";

   import { useState } from "react";

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

     const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

     const handleSend = async () => {
       if (!input.trim() || loading) return;

       const question = input.trim();
       setInput("");

       // Add user message
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
             content: "Sorry, something went wrong. Please try again.",
           },
         ]);
       } finally {
         setLoading(false);
       }
     };

     return (
       <main className="min-h-screen bg-gray-50 flex flex-col">
         {/* Nav */}
         <nav className="border-b bg-white px-6 py-4 flex justify-between items-center">
           <a href="/" className="text-xl font-bold text-blue-700">ClinIQ</a>
           <a href="/upload" className="text-sm text-blue-600 hover:underline">
             Upload New Document
           </a>
         </nav>

         {/* Chat Messages */}
         <div className="flex-1 overflow-y-auto px-6 py-8 max-w-3xl mx-auto w-full">
           {messages.length === 0 && (
             <div className="text-center text-gray-400 mt-20">
               <p className="text-lg mb-2">Ask a question about your document</p>
               <p className="text-sm">
                 Try: "What is the primary endpoint?" or "List the inclusion criteria"
               </p>
             </div>
           )}

           {messages.map((msg, i) => (
             <div key={i} className={`mb-6 ${msg.role === "user" ? "text-right" : ""}`}>
               {/* Message bubble */}
               <div
                 className={`inline-block max-w-[85%] p-4 rounded-xl ${
                   msg.role === "user"
                     ? "bg-blue-600 text-white rounded-br-sm"
                     : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
                 }`}
               >
                 <p className="whitespace-pre-wrap">{msg.content}</p>
               </div>

               {/* Citation badges (for assistant messages) */}
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

           {loading && (
             <div className="mb-6">
               <div className="inline-block bg-white border border-gray-200 p-4 rounded-xl rounded-bl-sm">
                 <p className="text-gray-400">Searching document and generating answer...</p>
               </div>
             </div>
           )}
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
               className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
             />
             <button
               onClick={handleSend}
               disabled={loading || !input.trim()}
               className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition"
             >
               Ask
             </button>
           </div>
         </div>
       </main>
     );
   }