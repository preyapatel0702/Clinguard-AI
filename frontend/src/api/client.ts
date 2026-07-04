// API client for ClinGuard-AI.
//
// `request()` is the single seam every service call goes through (chat,
// audit, monitoring, pipeline) to reach the real backend at
// `VITE_API_BASE_URL`.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

/**
 * Thin fetch wrapper used by every service module to call the real
 * backend at `${API_BASE_URL}${path}`.
 */
export async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, headers, ...rest } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(
      `Request to ${path} failed with status ${response.status}`,
      response.status
    );
  }

  return (await response.json()) as T;
}

/** Simulates network latency for mock service calls in development. */
export function mockDelay(ms = 350): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface BlobResponse {
  blob: Blob;
  filename: string | null;
}

/** Extracts a filename from a Content-Disposition header, if present. */
function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Thin fetch wrapper for binary/file responses (exports, downloads), where
 * `request()`'s automatic `response.json()` parsing doesn't apply. Goes
 * through the same `API_BASE_URL` seam as `request()`.
 */
export async function requestBlob(
  path: string,
  options: RequestOptions = {}
): Promise<BlobResponse> {
  const { body, headers, ...rest } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(
      `Request to ${path} failed with status ${response.status}`,
      response.status
    );
  }

  const blob = await response.blob();
  const filename = filenameFromContentDisposition(
    response.headers.get("Content-Disposition")
  );

  return { blob, filename };
}
