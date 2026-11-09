import React from 'react';
import { Activity, ShieldCheck, Radio, Server } from 'lucide-react';
import { SystemMeta } from '../types/orion';

interface SystemStatusCardProps {
  meta: SystemMeta;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({ meta }) => {
  const isTailscaleActive = Boolean(
    meta.tailscaleAddr &&
    !meta.tailscaleAddr.includes('Not configured') &&
    meta.tailscaleAddr !== '__TAILSCALE_ADDR__'
  );

  const isLlmLinked = Boolean(
    meta.remoteLlmHost &&
    !meta.remoteLlmHost.includes('Disabled') &&
    meta.remoteLlmHost !== '__REMOTE_LLM_HOST__'
  );

  return (
    <section className="nexus-glass rounded-2xl p-4 md:p-5 flex flex-col space-y-3">
      <div className="flex items-center space-x-2 pb-2 border-b border-sky-900/30">
        <Activity className="w-3.5 h-3.5 text-cyan-400" />
        <h3 className="text-[11px] font-bold font-mono tracking-wider text-slate-400 uppercase">
          System Link & Telemetry
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[11px] font-mono">
        {/* Tailscale Status */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-sky-950/80 flex items-center space-x-2">
          <Radio className={`w-3.5 h-3.5 ${isTailscaleActive ? 'text-emerald-400 animate-pulse' : 'text-slate-500'}`} />
          <div className="truncate">
            <div className="text-[10px] text-slate-500 uppercase">MESH NETWORK</div>
            <div className="text-slate-200 font-bold truncate">
              {isTailscaleActive ? 'ONLINE // SECURE' : 'STANDALONE'}
            </div>
          </div>
        </div>

        {/* Neural Engine Status */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-sky-950/80 flex items-center space-x-2">
          <Server className={`w-3.5 h-3.5 ${isLlmLinked ? 'text-cyan-400' : 'text-slate-500'}`} />
          <div className="truncate">
            <div className="text-[10px] text-slate-500 uppercase">NEURAL ENGINE</div>
            <div className="text-slate-200 font-bold truncate">
              {isLlmLinked ? 'REMOTE LINKED' : 'LOCAL HOST'}
            </div>
          </div>
        </div>

        {/* Auth Shield */}
        <div className="p-2.5 rounded-xl bg-slate-950/70 border border-sky-950/80 flex items-center space-x-2">
          <ShieldCheck className={`w-3.5 h-3.5 ${meta.isAuthed ? 'text-emerald-400' : 'text-amber-400'}`} />
          <div className="truncate">
            <div className="text-[10px] text-slate-500 uppercase">SECURITY</div>
            <div className="text-slate-200 font-bold truncate">
              {meta.isAuthed ? 'AUTHENTICATED' : 'ANONYMOUS'}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
