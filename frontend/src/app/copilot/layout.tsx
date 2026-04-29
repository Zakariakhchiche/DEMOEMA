/**
 * Layout standalone /copilot — bypass le MainLayout app (sidebar EDRCF, header, etc.)
 *
 * Le mode Chat est une expérience full-screen autonome (à la ChatGPT). On évite
 * la double sidebar (EDRCF + ConversationsSidebar) qui surcharge le layout.
 */
export default function CopilotLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
