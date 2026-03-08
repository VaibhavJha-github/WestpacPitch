import { useState, useEffect, useCallback } from 'react';
import { fetchAppointments } from '../lib/api';
import { appointments as mockAppointments } from '../data/mockData';
import type { Appointment } from '../data/mockData';

export function useAppointments() {
  const [appointments, setAppointments] = useState<Appointment[]>(mockAppointments);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchAppointments();
      if (data && data.length > 0) {
        setAppointments(data);
        setIsLive(true);
      }
      setError(null);
    } catch {
      // Fall back to mock data silently
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Poll every 10s for live updates
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [load]);

  return { appointments, loading, error, isLive, refresh: load };
}
