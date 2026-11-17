import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  Briefcase,
  ExternalLink,
  Check,
  X,
  FileText,
  Mail,
  Files,
  Eye,
  Maximize2,
  Download,
  Loader2,
  Sparkles,
  RotateCcw,
} from 'lucide-react';
import { JobPendingResponse, CandidateJob } from '../types/orion';
import {
  resolveJob,
  selectCandidate,
  skipCandidate,
  skipAllCandidates,
  getJobPdfUrl,
  downloadPdfFile,
} from '../api/client';

interface JobBridgeCardProps {
  pendingBridge: JobPendingResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const JobBridgeCard: React.FC<JobBridgeCardProps> = ({
  pendingBridge,
  isLoading,
  onRefresh,
}) => {
  const [resolving, setResolving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [previewPdfFilename, setPreviewPdfFilename] = useState<string>('document.pdf');
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [selectingKey, setSelectingKey] = useState<string | null>(null);
  const [skippingKeys, setSkippingKeys] = useState<Set<string>>(new Set());
  const [skippingAll, setSkippingAll] = useState(false);

  useEffect(() => {
    if (previewPdfUrl) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [previewPdfUrl]);

  const handleResolve = async (approved: boolean) => {
    setResolving(true);
    setFeedback(null);
    try {
      const res = await resolveJob(approved);
      setFeedback(res.message || (approved ? 'Application Approved!' : 'Job Skipped.'));
      setTimeout(() => {
        setFeedback(null);
        onRefresh();
      }, 1200);
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setResolving(false);
    }
  };

  const handleSelectCandidate = async (jobKey: string) => {
    setSelectingKey(jobKey);
    setFeedback('Scraping posting and tailoring application documents...');
    try {
      await selectCandidate(jobKey);
      setTimeout(() => {
        onRefresh();
      }, 800);
    } catch (err: unknown) {
      setFeedback(err instanceof Error ? err.message : 'Selection failed');
    } finally {
      setSelectingKey(null);
    }
  };

  const handleSkipCandidate = async (jobKey: string) => {
    setSkippingKeys((prev) => new Set(prev).add(jobKey));
    try {
      await skipCandidate(jobKey);
      onRefresh();
    } catch (err: unknown) {
      console.error('Skip candidate error:', err);
    }
  };

  const handleSkipAll = async () => {
    if (!window.confirm('Skip all remaining candidate listings in this batch?')) return;
    setSkippingAll(true);
    try {
      await skipAllCandidates();
      setSkippingKeys(new Set());
      onRefresh();
    } catch (err: unknown) {
      console.error('Skip all error:', err);
    } finally {
      setSkippingAll(false);
    }
  };

  const pendingJob = pendingBridge?.job;
  const isScreenBatch = pendingBridge?.stage === 'screen_batch';
  const allCandidates: CandidateJob[] = pendingBridge?.candidates || [];
  const activeCandidates = allCandidates.filter((c) => !skippingKeys.has(c.job_key));

  const openPreview = (pdfFile: string, docLabel: string = 'Document') => {
    const url = getJobPdfUrl(pdfFile);
    const companyClean = (pendingJob?.company || 'Job').replace(/[^a-zA-Z0-9_-]/g, '_');
    const fileClean = pdfFile.split('/').pop() || `${docLabel}.pdf`;
    setPreviewPdfFilename(`${companyClean}_${fileClean}`);
    setPreviewPdfUrl(url);
  };

  const handleDownloadPdf = async () => {
    if (!previewPdfUrl || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      await downloadPdfFile(previewPdfUrl, previewPdfFilename);
    } catch (err: unknown) {
      console.error('Save PDF error:', err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const isPending = Boolean(pendingBridge && pendingBridge.pending);

  return (
    <>
      <section className="nexus-glass rounded-2xl p-4 md:p-5 flex flex-col space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-sky-900/30">
          <div className="flex items-center space-x-2">
            <Briefcase className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs md:text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">
              Job Application Bridge
            </h2>
          </div>
          <span
            className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border ${
              isLoading
                ? 'bg-slate-900 text-slate-500 border-slate-800'
                : isScreenBatch
                ? 'bg-cyan-950/50 text-cyan-300 border-cyan-500/40 font-semibold'
                : pendingJob
                ? 'bg-amber-950/40 text-amber-300 border-amber-500/40 animate-pulse font-semibold'
                : 'bg-slate-900 text-slate-500 border-slate-800'
            }`}
          >
            {isLoading
              ? 'POLLING...'
              : isScreenBatch
              ? `● ${activeCandidates.length} CANDIDATES READY`
              : pendingJob
              ? 'ACTION REQUIRED'
              : 'IDLE'}
          </span>
        </div>

        {/* Feedback / Notification Banner */}
        {feedback && (
          <div className="p-2.5 rounded-xl bg-sky-950/60 border border-cyan-500/30 text-center font-mono text-xs text-cyan-300 animate-fade-in flex items-center justify-center space-x-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
            <span>{feedback}</span>
          </div>
        )}

        {/* Empty State */}
        {!isPending && (
          <div className="py-7 text-center space-y-2">
            <div className="w-10 h-10 rounded-full bg-sky-950/40 border border-sky-800/30 flex items-center justify-center mx-auto text-sky-400/60">
              <Briefcase className="w-5 h-5" />
            </div>
            <p className="text-xs font-mono text-slate-400">No pending job applications waiting for approval.</p>
            <p className="text-[11px] text-slate-500">
              Applications queued by the headless scraper or CLI will appear here for 1-click review.
            </p>
          </div>
        )}

        {/* STAGE 1: Multi-Candidate Batch Screening State */}
        {isPending && isScreenBatch && (
          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between bg-slate-950/60 border border-sky-900/30 rounded-xl px-3 py-2 text-xs">
              <div className="flex items-center space-x-2">
                <span className="text-cyan-400 font-mono font-bold">
                  {activeCandidates.length} Listing{activeCandidates.length === 1 ? '' : 's'}
                </span>
                <span className="text-slate-400 text-[11px]">Ready to screen</span>
              </div>
              <button
                type="button"
                onClick={handleSkipAll}
                disabled={skippingAll}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-[11px] font-mono border border-slate-800 transition disabled:opacity-50"
              >
                <RotateCcw className="w-3 h-3 text-slate-400" />
                <span>Skip All & Next</span>
              </button>
            </div>

            {/* Candidates Scroll List */}
            <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
              {activeCandidates.map((c, i) => {
                const ageDays = typeof c.age_days === 'number' ? c.age_days : 999;
                let badgeColor = 'bg-slate-900 text-slate-400 border-slate-800';
                if (ageDays <= 3) {
                  badgeColor = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
                } else if (ageDays <= 10) {
                  badgeColor = 'bg-amber-500/20 text-amber-400 border-amber-500/40';
                }

                return (
                  <div
                    key={c.job_key || i}
                    className="p-3 bg-slate-950/70 hover:bg-slate-950 border border-sky-900/30 hover:border-cyan-500/40 rounded-xl transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm"
                  >
                    <div className="flex items-start sm:items-center space-x-3 min-w-0">
                      <span className="w-6 h-6 rounded-md bg-slate-900 border border-slate-800 text-cyan-300 font-mono text-xs flex items-center justify-center font-bold shrink-0">
                        #{c.index || i + 1}
                      </span>
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center space-x-2 flex-wrap">
                          <span className="font-bold text-sm text-white truncate max-w-[280px]">
                            {c.title || 'Unknown Role'}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border whitespace-nowrap ${badgeColor}`}
                          >
                            {c.age_label || 'Recent'}
                          </span>
                          {c.date_display && (
                            <span className="text-[10px] text-slate-500 hidden md:inline font-mono">
                              ({c.date_display})
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400 flex items-center space-x-1.5 flex-wrap">
                          <span className="text-cyan-300 font-medium">{c.company}</span>
                          <span className="text-slate-600">·</span>
                          <span className="text-slate-400 truncate max-w-[200px]">
                            {c.location || 'Remote'}
                          </span>
                          {c.terms && c.terms.length > 0 && (
                            <>
                              <span className="text-slate-600">·</span>
                              <span className="text-slate-500 text-[10px]">{c.terms.join(', ')}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1.5 shrink-0 self-end sm:self-center">
                      {c.url && (
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 text-xs font-mono transition"
                          title="Open Job Posting in new tab"
                        >
                          <span>View</span>
                          <ExternalLink className="w-3 h-3 text-cyan-400" />
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => handleSelectCandidate(c.job_key)}
                        disabled={selectingKey === c.job_key}
                        className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-mono font-bold text-xs transition shadow-sm disabled:opacity-50"
                      >
                        {selectingKey === c.job_key ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Tailoring...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3" />
                            <span>Tailor</span>
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSkipCandidate(c.job_key)}
                        className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/50 text-slate-400 hover:text-rose-300 border border-slate-800 hover:border-rose-900/50 transition"
                        title="Skip this listing"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* STAGE 2: Single Tailored Application Review State */}
        {isPending && !isScreenBatch && pendingJob && (
          <div className="space-y-4 pt-1">
            {/* Job Summary Banner */}
            <div className="bg-amber-950/20 border border-amber-500/30 rounded-xl p-3.5 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-bold px-2 py-0.5 bg-amber-500/10 rounded">
                  {pendingJob.stage === 'screen' ? 'Pre-Screening' : 'Ready for Final Review'}
                </span>
                {pendingJob.apply_url && pendingJob.apply_url !== 'N/A' && (
                  <a
                    href={pendingJob.apply_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-xs text-cyan-400 hover:text-cyan-300 underline font-mono"
                  >
                    <span>Posting</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
              <h3 className="text-base md:text-lg font-bold text-white tracking-tight">
                {pendingJob.title || 'Software Role'}
              </h3>
              <p className="text-xs font-medium text-slate-300">
                {pendingJob.company || 'Unknown Organization'}
              </p>
            </div>

            {/* Application Documents */}
            <div className="space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                Generated Documents
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() =>
                    openPreview(pendingJob.resume_pdf || pendingJob.cv_pdf || 'resume.pdf', 'Resume')
                  }
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-2 rounded-xl bg-slate-950/70 border border-sky-900/40 hover:border-cyan-500/50 text-slate-200 text-xs font-mono transition"
                >
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="truncate">Resume</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    openPreview(
                      pendingJob.cover_letter_pdf || pendingJob.cl_pdf || 'cover_letter.pdf',
                      'Cover_Letter'
                    )
                  }
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-2 rounded-xl bg-slate-950/70 border border-sky-900/40 hover:border-cyan-500/50 text-slate-200 text-xs font-mono transition"
                >
                  <Mail className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="truncate">Cover Letter</span>
                </button>
                <button
                  type="button"
                  onClick={() => openPreview(pendingJob.combined_pdf || 'combined.pdf', 'Combined')}
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-2 rounded-xl bg-cyan-950/40 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 text-xs font-mono font-bold transition"
                >
                  <Files className="w-3.5 h-3.5 text-cyan-300" />
                  <span className="truncate">Combined</span>
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <button
                type="button"
                onClick={() => handleResolve(true)}
                disabled={resolving}
                className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-mono font-bold text-xs md:text-sm transition shadow-lg shadow-emerald-950/50 disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                <span>APPROVE & OPEN</span>
              </button>
              <button
                type="button"
                onClick={() => handleResolve(false)}
                disabled={resolving}
                className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-slate-900 hover:bg-rose-950/50 hover:text-rose-300 active:scale-95 text-slate-400 border border-slate-800 hover:border-rose-800/50 font-mono text-xs md:text-sm transition disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                <span>SKIP JOB</span>
              </button>
            </div>
          </div>
        )}
      </section>

      {/* PDF Lightbox Modal */}
      {previewPdfUrl &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 bg-black/80 backdrop-blur-md animate-fade-in pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
            onClick={() => setPreviewPdfUrl(null)}
          >
            <div
              className="nexus-glass rounded-2xl w-full max-w-4xl h-[92vh] sm:h-[88vh] md:h-[85vh] flex flex-col overflow-hidden border border-cyan-500/40 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 sm:py-3 border-b border-sky-900/40 bg-slate-950/60">
                <div className="flex items-center space-x-2 text-xs font-mono text-cyan-300 min-w-0">
                  <Eye className="w-4 h-4 shrink-0" />
                  <span className="truncate">DOCUMENT PREVIEW (ZERO-LEAK)</span>
                </div>
                <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
                  <button
                    type="button"
                    onClick={handleDownloadPdf}
                    disabled={downloadingPdf}
                    className="flex items-center space-x-1 sm:space-x-1.5 px-2.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-slate-950 font-mono font-bold text-xs transition shadow-lg shadow-cyan-950/40 disabled:opacity-50"
                    title="Save PDF directly to device"
                  >
                    {downloadingPdf ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Download className="w-3.5 h-3.5" />
                    )}
                    <span className="hidden xs:inline">Save PDF</span>
                  </button>
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
                    title="Close preview"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <iframe
                src={previewPdfUrl}
                className="w-full flex-1 bg-white border-0"
                title="Application PDF Viewer"
              />
            </div>
          </div>,
          document.body
        )}
    </>
  );
};
