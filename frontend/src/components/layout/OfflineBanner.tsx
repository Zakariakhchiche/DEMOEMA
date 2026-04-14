"use client";

import { WifiOff } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

export default function OfflineBanner() {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[200] bg-amber-500 text-black px-4 py-2 flex items-center justify-center gap-2 text-xs font-black uppercase tracking-widest">
      <WifiOff size={14} />
      Mode hors ligne — données en cache
    </div>
  );
}
