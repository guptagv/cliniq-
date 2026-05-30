export default function Home() {
     return (
       <main className="min-h-screen flex items-center justify-center bg-gray-50">
         <div className="text-center">
           <h1 className="text-4xl font-bold text-gray-900 mb-4">
             ClinIQ
           </h1>
           <p className="text-lg text-gray-600 mb-8">
             AI-powered Q&A for clinical trial documents
           </p>
           <a
             href="/upload"
             className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
           >
             Upload a Document
           </a>
         </div>
       </main>
     );
   }