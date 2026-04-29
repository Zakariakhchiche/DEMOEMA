/**
 * Layout standalone /explorer — bypass MainLayout (sidebar EDRCF, etc.)
 * pour offrir une expérience full-screen comme /copilot.
 */
export default function ExplorerLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
