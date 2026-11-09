import React, { useState } from 'react';
import { Search, Loader2, Bot, CornerDownLeft, Copy, Check } from 'lucide-react';
import { executeSearch } from '../api/client';

export const QuickSearchCard: React.FC = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSearch = async () => {
    if (!query.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await executeSearch(query.trim());
      setResult(res.result || res.error || 'No response returned.');
    } catch (err: unknown) {
      setResult(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const copyResult = () => {
    if (!result) return;
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="nexus-glass rounded-2xl p-4 md:p-5 flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center space-x-2 pb-3 border-b border-sky-900/30">
        <Bot className="w-4 h-4 text-cyan-400" />
        <h2 className="text-xs md:text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">
          Orion Quick Search & Intelligence
        </h2>
      </div>

      {/* Input */}
      <div className="flex space-x-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Ask Orion or query the live web..."
            className="w-full pl-3.5 pr-8 py-2.5 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="button"
            onClick={handleSearch}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan-400"
            title="Press Enter to search"
          >
            <CornerDownLeft className="w-3.5 h-3.5" />
          </button>
        </div>
        <button
          type="button"
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 active:scale-95 text-cyan-300 border border-sky-800/40 rounded-xl text-xs font-mono font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
          <span className="hidden xs:inline">SEARCH</span>
        </button>
      </div>

      {/* Search Result Terminal Box */}
      {result && (
        <div className="bg-slate-950/90 border border-cyan-500/20 rounded-xl p-3.5 space-y-2 animate-fade-in">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 border-b border-slate-900 pb-1.5">
            <span className="text-cyan-400 font-bold">SYNTHESIS</span>
            <button
              onClick={copyResult}
              className="flex items-center space-x-1 hover:text-slate-200 transition"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'COPIED' : 'COPY'}</span>
            </button>
          </div>
          <div className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto custom-scroll">
            {result}
          </div>
        </div>
      )}
    </section>
  );
};
