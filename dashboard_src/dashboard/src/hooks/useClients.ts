import { useState, useEffect, useCallback } from 'react';
import { fetchClients, type ClientData } from '../lib/api';
import { getClientsFromAppointments } from '../data/clientsData';
import type { Client } from '../data/clientsData';

export function useClients() {
  const [clients, setClients] = useState<(ClientData | Client)[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchClients();
      if (data && data.length > 0) {
        setClients(data);
        setIsLive(true);
      } else {
        setClients(getClientsFromAppointments());
      }
    } catch {
      setClients(getClientsFromAppointments());
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { clients, loading, isLive, refresh: load };
}
