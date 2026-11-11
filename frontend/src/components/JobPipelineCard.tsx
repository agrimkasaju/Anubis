import React, { useState } from 'react';
import { Play, Square, Globe, Link2, Loader2, Sparkles } from 'lucide-react';
import { PipelineStatus } from '../types/orion';
import { startPipeline, stopPipeline } from '../api/client';

interface JobPipelineCardProps {
  status: PipelineStatus | null;
  onRefresh: () => void;
}

export const JobPipelineCard: React.FC<JobPipelineCardProps> = ({
  status,
  onRefresh,
}) => {
  const [mode, setMode] = useState<'scrape' | 'manual'>('scrape');
  const [seasons, setSeasons] = useState('all');
  const [locations, setLocations] = useState('all');
  const [roles, setRoles] = useState('all');
  const [url, setUrl] = useState('');
  const [company, setCompany] = useState('');
  const [title, setTitle] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isRunning = Boolean(status?.running);

  const handleStart = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      if (mode === 'manual' && !url.trim()) {
        setErrorMsg('Please enter a valid job posting URL.');
        setIsSubmitting(false);
        return;
      }
      await startPipeline({
        mode,
        seasons: mode === 'scrape' ? seasons : undefined,
        locations: mode === 'scrape' ? locations : undefined,
        roles: mode === 'scrape' ? roles : undefined,
        url: mode === 'manual' ? url.trim() : undefined,
        company: mode === 'manual' ? company.trim() : undefined,
        title: mode === 'manual' ? title.trim() : undefined,
      });
      setTimeout(() => {
        onRefresh();
      }, 1000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to start pipeline');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStop = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await stopPipeline();
      setTimeout(() => {
        onRefresh();
      }, 800);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to stop pipeline');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="nexus-glass rounded-2xl p-4 md:p-5 flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-sky-900/30">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs md:text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">
            AI Job Search Pipeline
          </h2>
        </div>
        <span
          className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border ${
            isRunning
              ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/40 animate-pulse'
              : 'bg-slate-900 text-slate-500 border-slate-800'
          }`}
        >
          {isRunning ? '● RUNNING' : '● IDLE'}
        </span>
      </div>

      {/* Mode Switcher */}
      <div className="grid grid-cols-2 p-1 bg-slate-950/80 border border-sky-950/60 rounded-xl text-xs font-mono">
        <button
          type="button"
          onClick={() => setMode('scrape')}
          className={`flex items-center justify-center space-x-1.5 py-2 rounded-lg transition ${
            mode === 'scrape'
              ? 'bg-sky-950/80 text-cyan-300 font-bold border border-cyan-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          <span>Auto-Scrape</span>
        </button>
        <button
          type="button"
          onClick={() => setMode('manual')}
          className={`flex items-center justify-center space-x-1.5 py-2 rounded-lg transition ${
            mode === 'manual'
              ? 'bg-sky-950/80 text-cyan-300 font-bold border border-cyan-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Link2 className="w-3.5 h-3.5" />
          <span>Manual URL</span>
        </button>
      </div>

      {/* Scrape Controls */}
      {mode === 'scrape' && (
        <div className="space-y-3">
          <p className="text-[11px] font-mono text-slate-400 leading-relaxed">
            Headlessly scans Simplify 30-min feeds, applies semantic filters, drafts tailored CV & letters, and bridges them for review.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <div className="space-y-1">
              <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Season
              </label>
              <select
                value={seasons}
                onChange={(e) => setSeasons(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Seasons</option>
                <option value="summer">Summer Only</option>
                <option value="winter">Winter Only</option>
                <option value="fall">Fall Only</option>
                <option value="fall,winter">Fall & Winter</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Location
              </label>
              <select
                value={locations}
                onChange={(e) => setLocations(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Locations</option>
                <option value="canada">Canada Only</option>
                <option value="us">United States Only</option>
                <option value="canada,us">Canada & US</option>
                <option value="remote">Remote Only</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Role Domain
              </label>
              <select
                value={roles}
                onChange={(e) => setRoles(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Tech Roles</option>
                <option value="software">Software / SWE</option>
                <option value="hardware">Hardware / Firmware</option>
                <option value="ai">AI / ML / Data</option>
              </select>
            </div>
          </div>

          <button
            type="button"
            onClick={handleStart}
            disabled={isSubmitting || isRunning}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-slate-950 font-mono font-bold rounded-xl text-xs md:text-sm transition shadow-lg shadow-cyan-950/40 disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            <span>LAUNCH AUTO-SCRAPE SESSION</span>
          </button>
        </div>
      )}

      {/* Manual Controls */}
      {mode === 'manual' && (
        <div className="space-y-3">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Posting URL (LinkedIn, Greenhouse, Lever)..."
            className="w-full px-3.5 py-2.5 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
          />

          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Company (optional)"
              className="w-full px-3 py-2 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
            />
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Role Title (optional)"
              className="w-full px-3 py-2 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="button"
            onClick={handleStart}
            disabled={isSubmitting || isRunning}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-slate-950 font-mono font-bold rounded-xl text-xs md:text-sm transition shadow-lg shadow-cyan-950/40 disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            <span>TAILOR APPLICATION FOR URL</span>
          </button>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-center font-mono text-xs text-rose-300">
          {errorMsg}
        </div>
      )}

      {/* Live Pipeline Status Panel */}
      {isRunning && (
        <div className="bg-slate-950/90 border border-cyan-500/30 rounded-xl p-3.5 space-y-2 font-mono">
          <div className="flex items-center justify-between text-xs">
            <span className="text-cyan-300 font-bold truncate">
              {status?.status_text || 'Pipeline Active'}
            </span>
            {status?.pid && (
              <span className="text-[10px] text-slate-500">PID: {status.pid}</span>
            )}
          </div>
          {status?.current_job && (
            <div className="text-[11px] text-slate-400 truncate">
              Current: <span className="text-slate-200">{status.current_job}</span>
            </div>
          )}
          <button
            type="button"
            onClick={handleStop}
            disabled={isSubmitting}
            className="w-full flex items-center justify-center space-x-1.5 py-1.5 text-xs text-rose-400 hover:text-rose-300 border border-rose-900/50 bg-rose-950/30 rounded-lg transition mt-1 font-mono disabled:opacity-50"
          >
            <Square className="w-3 h-3 fill-current" />
            <span>STOP BACKGROUND PIPELINE</span>
          </button>
        </div>
      )}
    </section>
  );
};
