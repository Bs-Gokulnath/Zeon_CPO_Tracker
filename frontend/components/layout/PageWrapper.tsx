import { Navbar } from "./Navbar";

interface PageWrapperProps {
  children: React.ReactNode;
  fullHeight?: boolean;
}

export function PageWrapper({ children, fullHeight = false }: PageWrapperProps) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className={fullHeight ? "flex-1 flex overflow-hidden" : "flex-1"}>
        {children}
      </main>
    </div>
  );
}
