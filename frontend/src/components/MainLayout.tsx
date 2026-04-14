"use client";

import Sidebar from "@/components/Sidebar";
import { CommandPalette } from "@/components/CommandPalette";
import GlobalCopilot from "@/components/GlobalCopilot";
import BottomTabBar from "@/components/layout/BottomTabBar";
import MobileHeader from "@/components/layout/MobileHeader";
import OfflineBanner from "@/components/layout/OfflineBanner";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <OfflineBanner />

      {/* Desktop Sidebar */}
      <div className="print:hidden hidden lg:block">
        <Sidebar />
      </div>

      <main className="flex-1 lg:ml-72 min-h-screen relative flex flex-col w-full overflow-x-hidden pb-20 lg:pb-0">
        {/* Mobile Header */}
        <MobileHeader />

        {/* Ambient Background — desktop only for GPU performance */}
        <div className="fixed inset-0 overflow-hidden -z-10 pointer-events-none hidden lg:block">
          <div className="absolute -top-[10%] -right-[5%] w-[40%] h-[40%] rounded-full bg-indigo-500/10 blur-[120px]" />
          <div className="absolute top-[30%] -left-[5%] w-[30%] h-[30%] rounded-full bg-purple-500/5 blur-[100px]" />
          <div className="absolute bottom-0 right-[20%] w-[20%] h-[20%] rounded-full bg-indigo-500/5 blur-[100px]" />
        </div>

        <div className="flex-1 p-4 md:p-8">{children}</div>

        {/* Quick Access Helper — desktop only */}
        <div className="fixed bottom-6 right-6 z-40 hidden lg:block print:hidden">
          <div className="flex items-center gap-3 px-4 py-2.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-xl text-[10px] text-gray-400 font-black tracking-widest uppercase shadow-2xl">
            <span className="flex items-center gap-1.5 text-indigo-400">
              <span className="p-1 rounded bg-indigo-500/10 border border-indigo-500/20">
                ⌘
              </span>
              <span className="p-1 rounded bg-indigo-500/10 border border-indigo-500/20">
                K
              </span>
            </span>
            Search Intelligence
          </div>
        </div>
      </main>

      {/* Mobile Bottom Tab Bar */}
      <BottomTabBar />

      <div className="print:hidden">
        <CommandPalette />
        <GlobalCopilot />
      </div>
    </>
  );
}
