import React, { useState } from 'react';
import { Briefcase, ExternalLink, Check, X, FileText, Mail, Files, Eye, Maximize2 } from 'lucide-react';
import { PendingJob } from '../types/orion';
import { resolveJob, getJobPdfUrl } from '../api/client';

interface JobBridgeCardProps {
  pendingJob: PendingJob | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const JobBridgeCard: React.FC<JobBridgeCardProps> = ({
  pendingJob,
  isLoading,
  onRefresh,
}) => {
  const [resolving, setResolving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);

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

  const openPreview = (pdfFile: string) => {
    setPreviewPdfUrl(getJobPdfUrl(pdfFile));
  };

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
              pendingJob
                ? 'bg-amber-950/40 text-amber-300 border-amber-500/40 animate-pulse'
                : 'bg-slate-900 text-slate-500 border-slate-800'
            }`}
          >
            {isLoading ? 'POLLING...' : pendingJob ? 'ACTION REQUIRED' : 'IDLE'}
          </span>
        </div>

        {/* Empty State */}
        {!pendingJob && (
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

        {/* Pending State */}
        {pendingJob && (
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
              <h3 className="text-base md:text-lg font-bold text-white tracking-tight">{pendingJob.title || 'Software Role'}</h3>
              <p className="text-xs font-medium text-slate-300">{pendingJob.company || 'Unknown Organization'}</p>
            </div>

            {/* Application Documents */}
            <div className="space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                Generated Documents
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => openPreview(pendingJob.resume_pdf || 'resume.pdf')}
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-2 rounded-xl bg-slate-950/70 border border-sky-900/40 hover:border-cyan-500/50 text-slate-200 text-xs font-mono transition"
                >
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="truncate">Resume</span>
                </button>
                <button
                  type="button"
                  onClick={() => openPreview(pendingJob.cover_letter_pdf || 'cover_letter.pdf')}
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-2 rounded-xl bg-slate-950/70 border border-sky-900/40 hover:border-cyan-500/50 text-slate-200 text-xs font-mono transition"
                >
                  <Mail className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="truncate">Cover Letter</span>
                </button>
                <button
                  type="button"
                  onClick={() => openPreview(pendingJob.combined_pdf || 'combined.pdf')}
                  className="flex items-center justify-center space-x-1.5 py-2.5 px-2 rounded-xl bg-cyan-950/40 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 text-xs font-mono font-bold transition"
                >
                  <Files className="w-3.5 h-3.5 text-cyan-300" />
                  <span className="truncate">Combined</span>
                </button>
              </div>
            </div>

            {/* Feedback / Status */}
            {feedback && (
              <div className="p-2.5 rounded-xl bg-sky-950/60 border border-cyan-500/30 text-center font-mono text-xs text-cyan-300 animate-fade-in">
                {feedback}
              </div>
            )}

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
                <span>DOCUMENT PREVIEW (ZERO-LEAK)</span>
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
              title="Application PDF Viewer"
            />
          </div>
        </div>
      )}
    </>
  );
};
