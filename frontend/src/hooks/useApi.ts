import { useState, useEffect, useCallback } from 'react';


export function useApi<T>(endpoint: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(!!endpoint);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async (overriddenEndpoint?: string) => {
    const url = overriddenEndpoint || endpoint;
    if (!url) return;

    setLoading(true);
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }
      const json = await response.json();
      setData(json.data !== undefined ? json.data : json);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    if (endpoint) {
      fetchData();
    }
  }, [endpoint, fetchData]);

  return { data, loading, error, refetch: fetchData };
}
