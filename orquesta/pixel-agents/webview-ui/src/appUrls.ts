function trimLeadingSlash(value: string): string {
  return value.replace(/^\/+/, '');
}

function normalizeBaseUrl(baseUrl: string): string {
  if (!baseUrl || baseUrl === '.' || baseUrl === './') {
    return './';
  }
  return baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
}

export function buildAppUrl(baseUrl: string, relativePath: string): string {
  const cleanRelative = trimLeadingSlash(relativePath);
  const normalizedBase = normalizeBaseUrl(baseUrl);

  if (normalizedBase === './') {
    return new URL(cleanRelative, window.location.href).toString();
  }

  return new URL(cleanRelative, new URL(normalizedBase, window.location.origin)).toString();
}

export async function fetchJsonWithFallback<T>(
  baseUrl: string,
  relativePath: string,
  extraCandidates: string[] = [],
): Promise<T> {
  const candidates = [
    buildAppUrl(baseUrl, relativePath),
    ...extraCandidates.map((candidate) => buildAppUrl(baseUrl, candidate)),
    new URL(trimLeadingSlash(relativePath), window.location.origin + '/').toString(),
  ];

  let lastError: Error | null = null;

  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate);
      if (!response.ok) {
        lastError = new Error(`GET ${candidate} returned ${response.status.toString()}`);
        continue;
      }

      const contentType = response.headers.get('content-type') ?? '';
      const text = await response.text();
      if (!contentType.includes('application/json') && text.trimStart().startsWith('<')) {
        lastError = new Error(`GET ${candidate} returned HTML instead of JSON`);
        continue;
      }

      return JSON.parse(text) as T;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
    }
  }

  throw lastError ?? new Error(`No se pudo cargar JSON para ${relativePath}`);
}
