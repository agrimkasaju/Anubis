import React from 'react';
import { Terminal, RefreshCw, ShieldCheck, ShieldAlert, Cpu } from 'lucide-react';

interface NexusHeaderProps {
  onRefresh: () => void;
  isRefreshing: boolean;
  isAuthed: boolean;
  onOpenAuth: () => void;
}

export const NexusHeader: React.FC<NexusHeaderProps> = ({
  onRefresh,
  isRefreshing,
  isAuthed,
  onOpenAuth,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-sky-900/30 bg-[#06090F]/90 backdrop-blur-xl px-4 py-3">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        {/* Terminal Title */}
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping absolute opacity-75" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 relative" />
          </div>
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span className="font-mono text-xs md:text-sm font-bold tracking-wider text-slate-100 uppercase">
              ORION <span className="text-cyan-400">// NEXUS CORE</span>
            </span>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex items-center space-x-2.5">
          {/* Security Indicator */}
          <button
            onClick={onOpenAuth}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono border transition ${
              isAuthed
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30 hover:border-emerald-500/60'
                : 'bg-rose-950/40 text-rose-400 border-rose-500/30 hover:border-rose-500/60'
            }`}
            title={isAuthed ? 'Authenticated Session' : 'Click to Enter Access Token'}
          >
            {isAuthed ? <ShieldCheck className="w-3 h-3 text-emerald-400" /> : <ShieldAlert className="w-3 h-3 text-rose-400" />}
            <span className="hidden sm:inline">{isAuthed ? 'AUTH: SECURE' : 'AUTH: LOCKED'}</span>
          </button>

          {/* Device Responsive Pill */}
          <div className="hidden sm:flex items-center space-x-1 px-2.5 py-1 text-[11px] font-mono rounded-lg bg-sky-950/30 text-sky-400/80 border border-sky-800/30">
            <Cpu className="w-3 h-3" />
            <span>AUTO-RESPONSIVE</span>
          </div>

          {/* Refresh Action */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-1 px-3 py-1 rounded-lg text-xs font-mono bg-sky-950/50 hover:bg-sky-900/50 active:scale-95 text-cyan-300 border border-sky-500/30 transition disabled:opacity-50"
            title="Refresh All Feeds"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span className="hidden xs:inline">SYNC</span>
          </button>
        </div>
      </div>
    </header>
  );
};
