import React, { useState, useEffect } from 'react';
import { TrendingUp, ArrowUpRight, Share2, Eye, ChevronDown, ChevronUp, Loader2, Sparkles, X, Maximize2 } from 'lucide-react';
import { StockData } from '../types/orion';
import { fetchStockAnalysis, fetchStockHistory, downloadStockPdf } from '../api/client';

export const StockIntelligenceCard: React.FC = () => {
  const [tickerInput, setTickerInput] = useState('');
  const [stockData, setStockData] = useState<StockData | null>(null);
  const [recentHistory, setRecentHistory] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [showFullAnalysis, setShowFullAnalysis] = useState(false);
  const [showThinking, setShowThinking] = useState(false);
  const [chartLightbox, setChartLightbox] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchStockHistory()
      .then((items) => {
        if (items && items.length > 0) {
          setRecentHistory(items);
          setStockData(items[0]);
        }
      })
      .catch(() => {});
  }, []);

  const handleAnalyze = async (symbolToAnalyze?: string) => {
    const symbol = (symbolToAnalyze || tickerInput).trim().toUpperCase();
    if (!symbol || loading) return;

    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchStockAnalysis(symbol);
      setStockData(data);
      // Refresh history pills
      const updatedHist = await fetchStockHistory();
      setRecentHistory(updatedHist);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!stockData || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      await downloadStockPdf(stockData.symbol);
    } catch {
      setErrorMsg('Failed to download PDF report');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const getSessionPill = (session?: string) => {
    if (!session) return null;
    const s = session.toLowerCase();
    if (s.includes('pre')) {
      return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">PRE</span>;
    }
    if (s.includes('after') || s.includes('ah')) {
      return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">AH</span>;
    }
    if (s.includes('overnight') || s.includes('24h') || s.includes('ats')) {
      return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">ON</span>;
    }
    return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">REG</span>;
  };

  return (
    <>
      <section className="nexus-glass rounded-2xl p-4 md:p-5 flex flex-col space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-sky-900/30">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs md:text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">
              Stock Intelligence
            </h2>
          </div>
          <span className="text-[10px] font-mono text-cyan-400/80">LLM Quantitative</span>
        </div>

        {/* Quick History Pills */}
        {recentHistory.length > 0 && (
          <div className="flex items-center space-x-1.5 overflow-x-auto custom-scroll pb-1">
            {recentHistory.slice(0, 6).map((item) => (
              <button
                key={item.symbol}
                type="button"
                onClick={() => {
                  setTickerInput(item.symbol);
                  setStockData(item);
                }}
                className={`px-2 py-1 rounded-lg text-[11px] font-mono transition whitespace-nowrap border ${
                  stockData?.symbol === item.symbol
                    ? 'bg-cyan-950/70 border-cyan-500/50 text-cyan-300 font-bold'
                    : 'bg-slate-950/60 border-sky-950 text-slate-400 hover:text-slate-200'
                }`}
              >
                {item.symbol}
              </button>
            ))}
          </div>
        )}

        {/* Input & Search */}
        <div className="flex space-x-2">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            placeholder="TICKER (NVDA, AAPL, SPY)..."
            className="flex-1 px-3.5 py-2.5 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono uppercase text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="button"
            onClick={() => handleAnalyze()}
            disabled={loading || !tickerInput.trim()}
            className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-slate-950 font-mono font-bold rounded-xl text-xs transition shadow-lg shadow-cyan-950/40 disabled:opacity-50 flex items-center space-x-1.5"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span>ANALYZE</span>
          </button>
        </div>

        {/* Error message */}
        {errorMsg && (
          <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-center font-mono text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="py-8 text-center space-y-2">
            <Loader2 className="w-6 h-6 text-cyan-400 animate-spin mx-auto" />
            <p className="text-xs font-mono text-slate-400">Evaluating multi-timeframe quantitative stance...</p>
          </div>
        )}

        {/* Stock Detail Card */}
        {stockData && !loading && (
          <div className="space-y-3 pt-1">
            {/* Ticker & Price Banner */}
            <div className="bg-slate-950/80 border border-sky-900/40 rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-lg md:text-xl font-mono font-black text-white">{stockData.symbol}</span>
                  {getSessionPill(stockData.market_session)}
                </div>
                <div className="flex items-center space-x-2">
                  <span
                    className={`px-2 py-0.5 rounded-lg text-[11px] font-mono font-bold uppercase tracking-wider border ${
                      stockData.stance === 'BULLISH'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : stockData.stance === 'BEARISH'
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}
                  >
                    {stockData.stance}
                  </span>
                  <button
                    type="button"
                    onClick={handleDownloadPdf}
                    disabled={downloadingPdf}
                    className="p-1.5 rounded-lg bg-sky-950/60 hover:bg-sky-900/60 text-cyan-300 border border-sky-700/40 transition active:scale-95"
                    title="Export Zero-Leak PDF Report"
                  >
                    {downloadingPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div className="flex items-baseline justify-between text-xs font-mono">
                <div className="flex items-baseline space-x-2">
                  <span className="text-xl md:text-2xl font-bold text-white">
                    {stockData.price !== null && stockData.price !== undefined
                      ? `$${stockData.price.toFixed(2)}`
                      : 'N/A'}
                  </span>
                  {stockData.range && <span className="text-[11px] text-slate-400">{stockData.range}</span>}
                </div>
              </div>

              {stockData.overnight_futures && (
                <div className="text-[10px] font-mono text-cyan-400/90 border-t border-sky-950 pt-1.5">
                  Overnight / Futures: {stockData.overnight_futures}
                </div>
              )}

              {stockData.news_call && (
                <div className="text-[11px] font-mono text-slate-400 border-t border-sky-950 pt-1.5">
                  News Catalyst: <span className="text-slate-300">{stockData.news_call}</span>
                </div>
              )}
            </div>

            {/* 14-Day Candlestick Chart Preview */}
            {stockData.chart_url && (
              <div className="bg-slate-950/80 border border-sky-900/40 rounded-xl p-2.5 space-y-1.5">
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                  <span>14-Day Candlestick Action</span>
                  <button
                    type="button"
                    onClick={() => setChartLightbox(stockData.chart_url)}
                    className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300"
                  >
                    <Eye className="w-3 h-3" />
                    <span>Expand</span>
                  </button>
                </div>
                <div
                  className="cursor-pointer group relative rounded-lg overflow-hidden border border-slate-900 bg-slate-950"
                  onClick={() => setChartLightbox(stockData.chart_url)}
                >
                  <img
                    src={stockData.chart_url}
                    alt={`${stockData.symbol} chart`}
                    className="w-full h-32 md:h-40 object-contain object-center group-hover:scale-[1.02] transition duration-300"
                  />
                  <div className="absolute inset-0 bg-cyan-950/20 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                    <Maximize2 className="w-5 h-5 text-cyan-300" />
                  </div>
                </div>
              </div>
            )}

            {/* Full Analysis Accordion */}
            {stockData.raw_analysis && (
              <div className="border border-sky-900/30 rounded-xl bg-slate-950/50 overflow-hidden font-mono text-xs">
                <button
                  type="button"
                  onClick={() => setShowFullAnalysis(!showFullAnalysis)}
                  className="w-full flex items-center justify-between p-3 text-slate-400 hover:text-slate-200 transition text-left"
                >
                  <span className="text-[11px] font-bold text-cyan-400">View Full Quantitative Breakdown</span>
                  {showFullAnalysis ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {showFullAnalysis && (
                  <div className="p-3 pt-0 border-t border-sky-950 text-[11px] text-slate-300 whitespace-pre-wrap max-h-56 overflow-y-auto custom-scroll leading-relaxed">
                    {stockData.raw_analysis}
                  </div>
                )}
              </div>
            )}

            {/* AI Thinking Accordion */}
            {stockData.thinking_process && (
              <div className="border border-sky-900/30 rounded-xl bg-slate-950/50 overflow-hidden font-mono text-xs">
                <button
                  type="button"
                  onClick={() => setShowThinking(!showThinking)}
                  className="w-full flex items-center justify-between p-3 text-slate-400 hover:text-slate-200 transition text-left"
                >
                  <span className="text-[11px] font-bold text-purple-400">AI Reasoning & Data Lineage</span>
                  {showThinking ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {showThinking && (
                  <div className="p-3 pt-0 border-t border-sky-950 text-[11px] text-slate-400 whitespace-pre-wrap max-h-56 overflow-y-auto custom-scroll leading-relaxed">
                    {stockData.thinking_process}
                  </div>
                )}
              </div>
            )}

            {/* Launch Stock Terminal Button (Zero leak - no internal port numbers in label) */}
            <a
              href={`//${window.location.hostname}:8000`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-center space-x-1.5 w-full py-2.5 rounded-xl bg-sky-950/60 hover:bg-sky-900/60 text-cyan-300 font-mono text-xs transition border border-sky-800/40"
            >
              <span>Launch Full Stock Terminal</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </a>
          </div>
        )}
      </section>

      {/* Chart Lightbox Modal */}
      {chartLightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/85 backdrop-blur-md animate-fade-in"
          onClick={() => setChartLightbox(null)}
        >
          <div
            className="nexus-glass rounded-2xl max-w-4xl w-full p-4 border border-cyan-500/40 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-sky-900/40 pb-2">
              <span className="font-mono text-xs text-cyan-300 font-bold">14-DAY HIGH RESOLUTION CHART</span>
              <button
                type="button"
                onClick={() => setChartLightbox(null)}
                className="p-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <img
              src={chartLightbox}
              alt="Expanded Chart"
              className="w-full max-h-[75vh] object-contain rounded-xl bg-slate-950"
            />
          </div>
        </div>
      )}
    </>
  );
};
