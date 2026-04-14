"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Target, Network, Layers, Activity } from "lucide-react";
import { useEffect, useState } from "react";

const tabs = [
  { label: "Board", icon: LayoutDashboard, href: "/" },
  { label: "Vault", icon: Target, href: "/targets" },
  { label: "Graphe", icon: Network, href: "/graph" },
  { label: "Pipeline", icon: Layers, href: "/pipeline" },
  { label: "Signaux", icon: Activity, href: "/signals" },
];

export default function BottomTabBar() {
  const pathname = usePathname();
  const [signalCount, setSignalCount] = useState(0);

  useEffect(() => {
    fetch("/api/targets")
      .then((res) => res.json())
      .then((data) => {
        const count = (data.data || []).reduce(
          (acc: number, t: { topSignals?: unknown[] }) =>
            acc + (t.topSignals?.length || 0),
          0
        );
        setSignalCount(count);
      })
      .catch(() => {});
  }, []);

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-[100] lg:hidden print:hidden border-t border-white/10 bg-black/80 backdrop-blur-lg"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <div className="flex items-center justify-around h-16">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive =
            pathname === tab.href ||
            (tab.href !== "/" && pathname.startsWith(tab.href));

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-col items-center justify-center gap-1 w-full h-full relative transition-colors duration-200 ${
                isActive ? "text-indigo-400" : "text-gray-500 active:text-gray-300"
              }`}
            >
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-indigo-500" />
              )}
              <span className="relative">
                <Icon size={20} strokeWidth={isActive ? 2.5 : 1.8} />
                {tab.href === "/signals" && signalCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 min-w-[16px] h-4 px-1 flex items-center justify-center rounded-full bg-amber-500 text-[9px] font-black text-black">
                    {signalCount > 99 ? "99+" : signalCount}
                  </span>
                )}
              </span>
              <span
                className={`text-[10px] font-bold tracking-wide ${
                  isActive ? "text-indigo-400" : "text-gray-600"
                }`}
              >
                {tab.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
