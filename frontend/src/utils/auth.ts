const PRIMARY_KEY = 'orion_token';
const BACKUP_KEY = 'orion_auth_token';

/**
 * Initializes and retrieves auth token from URL query params, sessionStorage, or localStorage.
 * Maintains full backwards compatibility with legacy desktop browsers that saved 'orion_token' in localStorage.
 * Immediately scrubs ?token= from the address bar to prevent shoulder-surfing and log leakages.
 */
export function initAuthToken(): string {
  if (typeof window === 'undefined') return '';

  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get('token');

  if (urlToken) {
    sessionStorage.setItem(PRIMARY_KEY, urlToken);
    localStorage.setItem(PRIMARY_KEY, urlToken);

    // Scrub ?token= from address bar
    params.delete('token');
    const newQuery = params.toString() ? `?${params.toString()}` : '';
    const cleanUrl = `${window.location.pathname}${newQuery}${window.location.hash}`;
    window.history.replaceState({}, document.title, cleanUrl);
    return urlToken;
  }

  return getStoredToken();
}

export function getStoredToken(): string {
  if (typeof window === 'undefined') return '';
  return (
    sessionStorage.getItem(PRIMARY_KEY) ||
    localStorage.getItem(PRIMARY_KEY) ||
    sessionStorage.getItem(BACKUP_KEY) ||
    localStorage.getItem(BACKUP_KEY) ||
    ''
  );
}

export function setStoredToken(token: string): void {
  if (typeof window === 'undefined') return;
  if (token) {
    sessionStorage.setItem(PRIMARY_KEY, token);
    localStorage.setItem(PRIMARY_KEY, token);
  } else {
    sessionStorage.removeItem(PRIMARY_KEY);
    sessionStorage.removeItem(BACKUP_KEY);
    localStorage.removeItem(PRIMARY_KEY);
    localStorage.removeItem(BACKUP_KEY);
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
