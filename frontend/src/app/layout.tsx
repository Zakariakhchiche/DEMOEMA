import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { CommandPalette } from "@/components/CommandPalette";
import GlobalCopilot from "@/components/GlobalCopilot";
import { useState } from "react";
import { Menu, X, Zap } from "lucide-react";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Aethelgard | AI Origination Engine",
  description: "Proprietary intelligence for M&A and Private Equity origination.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${outfit.variable} antialiased bg-[#020202] text-gray-100 min-h-screen font-sans flex overflow-x-hidden`}
      >
        <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
        
        <main className="flex-1 lg:ml-72 min-h-screen relative flex flex-col w-full">
          {/* Mobile Header */}
          <header className="lg:hidden flex items-center justify-between p-6 bg-black/40 backdrop-blur-3xl border-b border-white/5 sticky top-0 z-[80]">
            <div className="flex items-center gap-3">
               <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                  <Zap size={16} className="text-white" />
               </div>
               <span className="text-white font-black text-sm tracking-tighter uppercase block leading-none">Aethelgard</span>
            </div>
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400"
            >
              <Menu size={20} />
            </button>
          </header>

          {/* Global Ambient Background */}
          <div className="fixed inset-0 overflow-hidden -z-10 pointer-events-none">
            <div className="absolute -top-[10%] -right-[5%] w-[40%] h-[40%] rounded-full bg-indigo-500/10 blur-[120px] animate-pulse" />
            <div className="absolute top-[30%] -left-[5%] w-[30%] h-[30%] rounded-full bg-purple-500/5 blur-[100px]" />
            <div className="absolute bottom-0 right-[20%] w-[20%] h-[20%] rounded-full bg-indigo-500/5 blur-[100px]" />
          </div>
          
          <div className="flex-1 p-4 md:p-8">
            {children}
          </div>

          {/* Quick Access Helper */}
          <div className="fixed bottom-6 right-6 z-40 hidden md:block">
             <div className="flex items-center gap-3 px-4 py-2.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-xl text-[10px] text-gray-400 font-black tracking-widest uppercase shadow-2xl">
                <span className="flex items-center gap-1.5 text-indigo-400">
                   <span className="p-1 rounded bg-indigo-500/10 border border-indigo-500/20">⌘</span> 
                   <span className="p-1 rounded bg-indigo-500/10 border border-indigo-500/20">K</span>
                </span> 
                Search Intelligence
             </div>
          </div>
        </main>

        <CommandPalette />
        <GlobalCopilot />
      </body>
    </html>
  );
}

