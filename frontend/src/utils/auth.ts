const TOKEN_STORAGE_KEY = 'orion_auth_token';

/**
 * Initializes and retrieves auth token from URL query params or sessionStorage.
 * Immediately scrubs the token from the browser address bar to prevent shoulder-surfing and leakages.
 */
export function initAuthToken(): string {
  if (typeof window === 'undefined') return '';

  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get('token');

  if (urlToken) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, urlToken);
    // Scrub ?token= from address bar
    params.delete('token');
    const newQuery = params.toString() ? `?${params.toString()}` : '';
    const cleanUrl = `${window.location.pathname}${newQuery}${window.location.hash}`;
    window.history.replaceState({}, document.title, cleanUrl);
    return urlToken;
  }

  return sessionStorage.getItem(TOKEN_STORAGE_KEY) || '';
}

export function getStoredToken(): string {
  if (typeof window === 'undefined') return '';
  return sessionStorage.getItem(TOKEN_STORAGE_KEY) || '';
}

export function setStoredToken(token: string): void {
  if (typeof window === 'undefined') return;
  if (token) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function getAuthHeaders(): HeadersInit {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}
