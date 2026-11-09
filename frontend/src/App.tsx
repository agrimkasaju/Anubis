import React, { useState, useEffect, useCallback } from 'react';
import { NexusHeader } from './components/NexusHeader';
import { JobBridgeCard } from './components/JobBridgeCard';
import { JobPipelineCard } from './components/JobPipelineCard';
import { JobHistoryCard } from './components/JobHistoryCard';
import { QuickSearchCard } from './components/QuickSearchCard';
import { StockIntelligenceCard } from './components/StockIntelligenceCard';
import { SystemStatusCard } from './components/SystemStatusCard';
import { AuthModal } from './components/AuthModal';
import { initAuthToken, getStoredToken } from './utils/auth';
import { fetchPendingJob, fetchPipelineStatus } from './api/client';
import { PendingJob, PipelineStatus, SystemMeta } from './types/orion';

export const App: React.FC = () => {
  const [token, setToken] = useState('');
  const [pendingJob, setPendingJob] = useState<PendingJob | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isBridgeLoading, setIsBridgeLoading] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [systemMeta, setSystemMeta] = useState<SystemMeta>({
    tailscaleAddr: '',
    remoteLlmHost: '',
    isAuthed: false,
  });

  // Initialize Auth Token on Mount and Scrub Address Bar
  useEffect(() => {
    const initialToken = initAuthToken();
    setToken(initialToken);

    // Read injected meta tags
    const tailscaleMeta = document.querySelector('meta[name="tailscale-addr"]')?.getAttribute('content') || '';
    const remoteLlmMeta = document.querySelector('meta[name="remote-llm-host"]')?.getAttribute('content') || '';

    setSystemMeta({
      tailscaleAddr: tailscaleMeta,
      remoteLlmHost: remoteLlmMeta,
      isAuthed: Boolean(initialToken),
    });

    if (!initialToken) {
      setAuthModalOpen(true);
    }
  }, []);

  const refreshFeeds = useCallback(async () => {
    setIsRefreshing(true);
    setIsBridgeLoading(true);

    try {
      // 1. Fetch Pending Job
      const jobRes = await fetchPendingJob();
      setPendingJob(jobRes.pending && jobRes.job ? jobRes.job : null);
    } catch {
      // If unauthorized, job bridge remains null
    } finally {
      setIsBridgeLoading(false);
    }

    try {
      // 2. Fetch Pipeline Status
      const pipeRes = await fetchPipelineStatus();
      setPipelineStatus(pipeRes);
    } catch {
      // Ignore background pipeline status error
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Initial load and periodic poll
  useEffect(() => {
    refreshFeeds();
    const interval = setInterval(() => {
      refreshFeeds();
    }, 8000);
    return () => clearInterval(interval);
  }, [refreshFeeds, token]);

  const handleAuthSuccess = () => {
    const updatedToken = getStoredToken();
    setToken(updatedToken);
    setSystemMeta((prev) => ({ ...prev, isAuthed: Boolean(updatedToken) }));
    refreshFeeds();
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#06090F] selection:bg-cyan-500 selection:text-black">
      {/* Top HUD Header */}
      <NexusHeader
        onRefresh={refreshFeeds}
        isRefreshing={isRefreshing}
        isAuthed={Boolean(token)}
        onOpenAuth={() => setAuthModalOpen(true)}
      />

      {/* Main Responsive Grid Layout */}
      <main className="max-w-6xl mx-auto w-full p-3 sm:p-5 md:p-6 flex-1 grid grid-cols-1 md:grid-cols-12 gap-5 md:gap-6">
        {/* Left Column (7 cols on desktop): Job Automation & AI Search */}
        <div className="md:col-span-7 flex flex-col space-y-5 md:space-y-6">
          <JobBridgeCard
            pendingJob={pendingJob}
            isLoading={isBridgeLoading}
            onRefresh={refreshFeeds}
          />

          <JobPipelineCard
            status={pipelineStatus}
            onRefresh={refreshFeeds}
          />

          <JobHistoryCard
            onHistoryChange={refreshFeeds}
          />

          <QuickSearchCard />
        </div>

        {/* Right Column (5 cols on desktop): Stock Intelligence & Telemetry */}
        <div className="md:col-span-5 flex flex-col space-y-5 md:space-y-6">
          <StockIntelligenceCard />

          <SystemStatusCard meta={systemMeta} />
        </div>
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
      />
    </div>
  );
};
