import { useState, useEffect, useCallback } from "react";
import { fetchAppointments } from "../lib/api";
import type { Appointment } from "../data/mockData";

const APPOINTMENTS_CACHE_KEY = "westpac_dashboard_appointments_cache_v1";

function readCachedAppointments(): Appointment[] {
  try {
    const raw = localStorage.getItem(APPOINTMENTS_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function useAppointments() {
  const [appointments, setAppointments] = useState<Appointment[]>(() =>
    readCachedAppointments(),
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchAppointments();
      setAppointments(data || []);
      localStorage.setItem(APPOINTMENTS_CACHE_KEY, JSON.stringify(data || []));
      setIsLive(true);
      setError(null);
    } catch {
      // Keep cached data if available; show non-blocking status in UI.
      setIsLive(false);
      setError(
        "Unable to fetch live appointments right now. Showing cached data.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Poll more frequently so new calls appear quickly in the demo.
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [load]);

  return { appointments, loading, error, isLive, refresh: load };
}
