import { getAuthHeaders, getStoredToken } from '../utils/auth';
import { JobPendingResponse, PipelineStatus, StockData, SearchResult } from '../types/orion';

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
