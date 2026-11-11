import { getAuthHeaders, getStoredToken } from '../utils/auth';
import { JobPendingResponse, PipelineStatus, StockData, SearchResult, JobHistoryResponse } from '../types/orion';

export async function fetchPendingJob(): Promise<JobPendingResponse> {
  const token = getStoredToken();
  const url = token ? `/api/job/pending?token=${encodeURIComponent(token)}` : '/api/job/pending';
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) {
    if (res.status === 401) throw new Error('Unauthorized');
    throw new Error(`Failed to fetch pending job: ${res.statusText}`);
  }
  return res.json();
}

export async function resolveJob(approved: boolean): Promise<{ status: string; approved: boolean; message: string }> {
  const token = getStoredToken();
  const url = token ? `/api/job/resolve?token=${encodeURIComponent(token)}` : '/api/job/resolve';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ approved }),
  });
  if (!res.ok) throw new Error(`Failed to resolve job: ${res.statusText}`);
  return res.json();
}

export async function fetchPipelineStatus(): Promise<PipelineStatus> {
  const token = getStoredToken();
  const url = token ? `/api/job/status?token=${encodeURIComponent(token)}` : '/api/job/status';
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Pipeline status error: ${res.statusText}`);
  return res.json();
}

export async function startPipeline(payload: {
  mode: 'scrape' | 'manual';
  seasons?: string;
  locations?: string;
  roles?: string;
  url?: string;
  company?: string;
  title?: string;
}): Promise<{ status: string; pid?: number; message?: string }> {
  const token = getStoredToken();
  const url = token ? `/api/job/start?token=${encodeURIComponent(token)}` : '/api/job/start';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to start pipeline: ${res.statusText}`);
  return res.json();
}

export async function stopPipeline(): Promise<{ status: string }> {
  const token = getStoredToken();
  const url = token ? `/api/job/stop?token=${encodeURIComponent(token)}` : '/api/job/stop';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Failed to stop pipeline: ${res.statusText}`);
  return res.json();
}

export async function fetchStockAnalysis(symbol: string): Promise<StockData> {
  const token = getStoredToken();
  const query = new URLSearchParams({ symbol });
  if (token) query.set('token', token);
  const res = await fetch(`/api/stock?${query.toString()}`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Failed to analyze stock: ${res.statusText}`);
  return res.json();
}

export async function fetchStockHistory(): Promise<StockData[]> {
  const token = getStoredToken();
  const url = token ? `/api/stock/history?token=${encodeURIComponent(token)}` : '/api/stock/history';
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function executeSearch(query: string): Promise<SearchResult> {
  const token = getStoredToken();
  const params = new URLSearchParams({ q: query });
  if (token) params.set('token', token);
  const res = await fetch(`/api/search?${params.toString()}`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Search error: ${res.statusText}`);
  return res.json();
}

export async function downloadStockPdf(symbol: string): Promise<void> {
  const token = getStoredToken();
  const params = new URLSearchParams({ symbol });
  if (token) params.set('token', token);
  const res = await fetch(`/api/stock/pdf?${params.toString()}`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to generate PDF');
  const blob = await res.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = `${symbol}_Analysis.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(blobUrl);
}

export function getJobPdfUrl(fileName: string): string {
  const token = getStoredToken();
  const params = new URLSearchParams({ file: fileName });
  if (token) params.set('token', token);
  return `/api/job/pdf?${params.toString()}`;
}

export async function fetchJobHistory(): Promise<JobHistoryResponse> {
  const token = getStoredToken();
  const url = token ? `/api/job/history?token=${encodeURIComponent(token)}` : '/api/job/history';
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch job history: ${res.statusText}`);
  return res.json();
}

export async function removeJobHistory(jobKey: string): Promise<{ status: string; job_key: string; message?: string }> {
  const token = getStoredToken();
  const url = token ? `/api/job/history/remove?token=${encodeURIComponent(token)}` : '/api/job/history/remove';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ job_key: jobKey }),
  });
  if (!res.ok) throw new Error(`Failed to remove job: ${res.statusText}`);
  return res.json();
}

export async function reapplyJob(job: {
  job_key: string;
  company: string;
  title: string;
  apply_url?: string;
}): Promise<{ status: string; job_key: string; pid?: number; message?: string }> {
  const token = getStoredToken();
  const url = token ? `/api/job/history/reapply?token=${encodeURIComponent(token)}` : '/api/job/history/reapply';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(job),
  });
  if (!res.ok) throw new Error(`Failed to reapply job: ${res.statusText}`);
  return res.json();
}

export async function syncJobCalendar(): Promise<{
  status: string;
  action?: string;
  total_keys?: number;
  message?: string;
  html_link?: string;
}> {
  const token = getStoredToken();
  const url = token ? `/api/job/calendar/sync?token=${encodeURIComponent(token)}` : '/api/job/calendar/sync';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to sync calendar: ${res.statusText}`);
  return res.json();
}

export async function pullJobCalendar(): Promise<{
  status: string;
  new_keys_added?: number;
  total_applied_keys?: number;
  new_history_entries?: number;
  message?: string;
}> {
  const token = getStoredToken();
  const url = token ? `/api/job/calendar/pull?token=${encodeURIComponent(token)}` : '/api/job/calendar/pull';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to pull calendar sync: ${res.statusText}`);
  return res.json();
}

export async function fetchRawAppliedJobs(): Promise<{
  applied_keys: string[];
  count: number;
}> {
  const token = getStoredToken();
  const url = token ? `/api/job/applied_raw?token=${encodeURIComponent(token)}` : '/api/job/applied_raw';
  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch applied jobs: ${res.statusText}`);
  return res.json();
}

export async function importRawAppliedJobs(keys: string[] | string): Promise<{
  status: string;
  new_keys_added?: number;
  total_applied_keys?: number;
  message?: string;
}> {
  const token = getStoredToken();
  const url = token ? `/api/job/applied_raw?token=${encodeURIComponent(token)}` : '/api/job/applied_raw';
  const res = await fetch(url, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ keys }),
  });
  if (!res.ok) throw new Error(`Failed to import applied jobs: ${res.statusText}`);
  return res.json();
}
