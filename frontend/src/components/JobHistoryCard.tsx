import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  CheckCircle2,
  SkipForward,
  Trash2,
  RotateCcw,
  ExternalLink,
  FileText,
  Mail,
  Files,
  Search,
  Eye,
  Maximize2,
  X,
  RefreshCw,
  Sparkles,
  Inbox,
  Calendar,
} from 'lucide-react';
import { JobHistoryItem } from '../types/orion';
import { fetchJobHistory, removeJobHistory, reapplyJob, getJobPdfUrl, syncJobCalendar } from '../api/client';

interface JobHistoryCardProps {
  onHistoryChange?: () => void;
}

export const JobHistoryCard: React.FC<JobHistoryCardProps> = ({ onHistoryChange }) => {
  const [activeTab, setActiveTab] = useState<'applied' | 'skipped'>('applied');
  const [appliedJobs, setAppliedJobs] = useState<JobHistoryItem[]>([]);
  const [skippedJobs, setSkippedJobs] = useState<JobHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterQuery, setFilterQuery] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null);
  const [syncingCalendar, setSyncingCalendar] = useState(false);

  const handleCalendarSync = async () => {
    setSyncingCalendar(true);
    try {
      const res = await syncJobCalendar('all');
      setFeedback(res.message || 'Synced jobs to Google Calendar!');
      setTimeout(() => setFeedback(null), 5000);
      await loadHistory();
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Calendar sync failed');
      setTimeout(() => setFeedback(null), 4000);
    } finally {
      setSyncingCalendar(false);
    }
  };

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJobHistory();
      setAppliedJobs(data.applied || []);
      setSkippedJobs(data.skipped || []);
    } catch {
      // Ignore poll error if unauthed
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
    const interval = setInterval(loadHistory, 15000);
    return () => clearInterval(interval);
  }, [loadHistory]);

  const handleRemove = async (job: JobHistoryItem) => {
    setActionLoadingKey(job.job_key);
    try {
      await removeJobHistory(job.job_key);
      setFeedback(`"${job.company}" removed from history (unlocked for reapplication).`);
      await loadHistory();
      if (onHistoryChange) onHistoryChange();
      setTimeout(() => setFeedback(null), 3000);
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Failed to remove job');
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      setActionLoadingKey(null);
    }
  };

  const handleReapply = async (job: JobHistoryItem) => {
    setActionLoadingKey(job.job_key);
    try {
      const res = await reapplyJob({
        job_key: job.job_key,
        company: job.company,
        title: job.title,
        apply_url: job.apply_url,
      });
      setFeedback(res.message || `Reapplication queued for ${job.company}!`);
      await loadHistory();
      if (onHistoryChange) onHistoryChange();
      setTimeout(() => setFeedback(null), 4000);
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Failed to trigger reapplication');
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      setActionLoadingKey(null);
    }
  };

  const formatJobTime = (timestamp: number) => {
    if (!timestamp) return '';
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
    const d = new Date(timestamp * 1000);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const openPreview = (pdfFile: string) => {
    setPreviewPdfUrl(getJobPdfUrl(pdfFile));
  };

  // Filter current tab list
  const currentList = activeTab === 'applied' ? appliedJobs : skippedJobs;
  const filteredList = currentList.filter((item) => {
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase();
    return (
      item.company.toLowerCase().includes(q) ||
      item.title.toLowerCase().includes(q) ||
      item.job_key.toLowerCase().includes(q)
    );
  });

  return (
    <>
      <section className="nexus-glass rounded-2xl p-4 md:p-5 flex flex-col space-y-4">
        {/* Header & Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-sky-900/30 gap-2.5">
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs md:text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">
              Job Queue & History
            </h2>
          </div>

          {/* Tab Selector & Refresh */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center p-0.5 rounded-xl bg-slate-950/80 border border-sky-900/40 font-mono text-[11px]">
              <button
                type="button"
                onClick={() => setActiveTab('applied')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg transition ${
                  activeTab === 'applied'
                    ? 'bg-cyan-950/70 text-cyan-300 font-bold border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span>Recently Applied</span>
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                  {appliedJobs.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('skipped')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg transition ${
                  activeTab === 'skipped'
                    ? 'bg-amber-950/70 text-amber-300 font-bold border border-amber-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <SkipForward className="w-3 h-3 text-amber-400" />
                <span>Skipped Jobs</span>
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-950/60 text-amber-300 border border-amber-500/30">
                  {skippedJobs.length}
                </span>
              </button>
            </div>

            <div className="flex items-center space-x-1.5">
              <button
                type="button"
                onClick={handleCalendarSync}
                disabled={syncingCalendar || loading}
                className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-sky-950/60 hover:bg-sky-900/60 text-cyan-300 border border-sky-800/40 text-xs font-mono transition disabled:opacity-50"
                title="Sync applied & skipped jobs to Google Calendar"
              >
                <Calendar className={`w-3.5 h-3.5 ${syncingCalendar ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">Sync Calendar</span>
              </button>

              <button
                type="button"
                onClick={loadHistory}
                disabled={loading}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-cyan-300 border border-slate-800 transition disabled:opacity-50"
                title="Refresh History"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div className="p-2.5 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-center font-mono text-xs text-cyan-300 animate-fade-in flex items-center justify-center space-x-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>{feedback}</span>
          </div>
        )}

        {/* Search / Filter Filter Input */}
        {(appliedJobs.length > 0 || skippedJobs.length > 0) && (
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder={`Filter ${activeTab === 'applied' ? 'applied' : 'skipped'} jobs by company or title...`}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950/60 border border-sky-900/30 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/60 transition"
            />
            {filterQuery && (
              <button
                type="button"
                onClick={() => setFilterQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {/* Jobs List Container */}
        <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
          {filteredList.length === 0 ? (
            <div className="py-8 text-center space-y-2">
              <div className="w-9 h-9 rounded-full bg-slate-950/60 border border-sky-900/30 flex items-center justify-center mx-auto text-slate-500">
                <Inbox className="w-4 h-4" />
              </div>
              <p className="text-xs font-mono text-slate-400">
                {filterQuery
                  ? `No matching positions found for "${filterQuery}".`
                  : activeTab === 'applied'
                  ? 'No applied positions recorded yet.'
                  : 'No skipped positions in queue.'}
              </p>
              <p className="text-[11px] text-slate-500">
                {activeTab === 'applied'
                  ? 'Approved job applications from the dashboard will be tracked here.'
                  : 'Positions skipped for later can be removed here to unlock them for reapplication.'}
              </p>
            </div>
          ) : (
            filteredList.map((job) => {
              const isWorking = actionLoadingKey === job.job_key;
              return (
                <div
                  key={job.job_key}
                  className="p-3 rounded-xl bg-slate-950/50 border border-sky-950/80 hover:border-sky-800/50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                >
                  {/* Left: Job Meta */}
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      {activeTab === 'applied' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      ) : (
                        <SkipForward className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                      )}
                      <span className="font-bold text-white text-xs md:text-sm truncate">
                        {job.company}
                      </span>
                      {job.timestamp > 0 && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 border border-slate-800">
                          {formatJobTime(job.timestamp)}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
                      <span className="truncate">{job.title}</span>
                      {job.apply_url && job.apply_url !== 'N/A' && (
                        <a
                          href={job.apply_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:text-cyan-300 inline-flex items-center space-x-0.5 flex-shrink-0"
                          title="Open Application Posting"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>

                    {/* PDF Preview Pills (For Applied Jobs) */}
                    {activeTab === 'applied' && (job.resume_pdf || job.cover_letter_pdf || job.combined_pdf) && (
                      <div className="flex items-center space-x-1.5 pt-1">
                        {job.resume_pdf && (
                          <button
                            type="button"
                            onClick={() => openPreview(job.resume_pdf!)}
                            className="px-2 py-0.5 rounded-md bg-slate-900/90 hover:bg-sky-950 border border-sky-900/40 hover:border-cyan-500/40 text-[10px] font-mono text-cyan-300 flex items-center space-x-1 transition"
                            title="Preview Resume"
                          >
                            <FileText className="w-2.5 h-2.5 text-cyan-400" />
                            <span>Resume</span>
                          </button>
                        )}
                        {job.cover_letter_pdf && (
                          <button
                            type="button"
                            onClick={() => openPreview(job.cover_letter_pdf!)}
                            className="px-2 py-0.5 rounded-md bg-slate-900/90 hover:bg-sky-950 border border-sky-900/40 hover:border-cyan-500/40 text-[10px] font-mono text-cyan-300 flex items-center space-x-1 transition"
                            title="Preview Cover Letter"
                          >
                            <Mail className="w-2.5 h-2.5 text-cyan-400" />
                            <span>Cover Letter</span>
                          </button>
                        )}
                        {job.combined_pdf && (
                          <button
                            type="button"
                            onClick={() => openPreview(job.combined_pdf!)}
                            className="px-2 py-0.5 rounded-md bg-cyan-950/40 hover:bg-cyan-900/40 border border-cyan-500/30 text-[10px] font-mono text-cyan-300 flex items-center space-x-1 transition"
                            title="Preview Combined"
                          >
                            <Files className="w-2.5 h-2.5 text-cyan-300" />
                            <span>Combined</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Right Actions */}
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    {/* Reapply Action (Always available on skipped jobs, or applied jobs if desired) */}
                    {activeTab === 'skipped' && (
                      <button
                        type="button"
                        onClick={() => handleReapply(job)}
                        disabled={isWorking}
                        className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 active:scale-95 text-white font-mono font-bold text-xs transition shadow-md shadow-emerald-950/50 disabled:opacity-50"
                        title="Reapply: Unlocks position & launches tailoring pipeline"
                      >
                        <RotateCcw className={`w-3 h-3 ${isWorking ? 'animate-spin' : ''}`} />
                        <span>REAPPLY</span>
                      </button>
                    )}

                    {/* Remove Action */}
                    <button
                      type="button"
                      onClick={() => handleRemove(job)}
                      disabled={isWorking}
                      className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/50 hover:text-rose-300 active:scale-95 text-slate-500 border border-slate-800 hover:border-rose-800/40 font-mono text-xs transition disabled:opacity-50"
                      title={
                        activeTab === 'skipped'
                          ? 'Remove from skipped list (unlocks for reapplication)'
                          : 'Remove from applied list (allows re-applying)'
                      }
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* PDF Lightbox Modal */}
      {previewPdfUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/80 backdrop-blur-md animate-fade-in"
          onClick={() => setPreviewPdfUrl(null)}
        >
          <div
            className="nexus-glass rounded-2xl w-full max-w-4xl h-[85vh] flex flex-col overflow-hidden border border-cyan-500/40 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-sky-900/40 bg-slate-950/60">
              <div className="flex items-center space-x-2 text-xs font-mono text-cyan-300">
                <Eye className="w-4 h-4" />
                <span>ARCHIVED DOCUMENT PREVIEW</span>
              </div>
              <div className="flex items-center space-x-2">
                <a
                  href={previewPdfUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 rounded-lg bg-sky-950/60 hover:bg-sky-900/60 text-cyan-400 border border-sky-700/40"
                  title="Open in Full Tab"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewPdfUrl(null)}
                  className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <iframe
              src={previewPdfUrl}
              className="w-full flex-1 bg-white border-0"
              title="Archived PDF Viewer"
            />
          </div>
        </div>
      )}
    </>
  );
};
