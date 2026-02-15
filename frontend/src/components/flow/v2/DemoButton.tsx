import { ChevronLeft } from "lucide-react";
export function DemoButton({ onClick }: { onClick?: () => void }) {
  return (
    <div className="fixed right-0 bottom-10 z-[60] animate-side-pulse">
      <button
        type="button"
        onClick={onClick}
        className="flex flex-col items-center gap-3 bg-white/40 backdrop-blur-md border border-white/50 border-r-0 rounded-l-xl py-4 px-1.5 shadow-lg group hover:bg-white/60 transition-all"
      >
        <span className="vertical-text text-[10px] font-bold tracking-[0.2em] text-charcoal uppercase">
          Demo
        </span>
        <ChevronLeft className="text-river w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
      </button>
    </div>
  );
}
