import { BACKEND_URL } from './supabase';
import type { Appointment } from '../data/mockData';

export async function fetchAppointments(): Promise<Appointment[]> {
  const res = await fetch(`${BACKEND_URL}/api/appointments`);
  if (!res.ok) throw new Error('Failed to fetch appointments');
  return res.json();
}

export async function fetchAppointment(id: string): Promise<Appointment> {
  const res = await fetch(`${BACKEND_URL}/api/appointments/${id}`);
  if (!res.ok) throw new Error('Failed to fetch appointment');
  return res.json();
}

export interface AcceptSlotResponse {
  status: string;
  slot_id: string;
  sms?: {
    confirmation?: {
      status?: string;
      sid?: string;
      reason?: string;
      error?: string;
    };
    to?: string;
    crosssell_body?: string;
  };
}

export async function acceptSlot(appointmentId: string, slotId: string): Promise<AcceptSlotResponse> {
  const res = await fetch(`${BACKEND_URL}/api/appointments/${appointmentId}/accept`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot_id: slotId }),
  });
  if (!res.ok) throw new Error('Failed to accept slot');
  return res.json();
}

export interface ClientData {
  id: string;
  customerId: string;
  name: string;
  initials: string;
  companyName?: string;
  location?: string;
  profession?: string;
  tenure?: string;
  totalBankingValue?: string;
  totalAppointments: number;
  lastContactDate: string;
  averageSentiment: number;
}

export async function fetchClients(): Promise<ClientData[]> {
  const res = await fetch(`${BACKEND_URL}/api/clients`);
  if (!res.ok) throw new Error('Failed to fetch clients');
  return res.json();
}

export interface AnalyticsData {
  warm: Record<string, boolean>;
  today: {
    totalCalls: number;
    completedAppointments: number;
    avgCallDuration: string;
    avgTTFA: string;
    escalationCount: number;
    conversionRate: number;
  };
  sentiment: {
    positive: number;
    neutral: number;
    anxious: number;
    frustrated: number;
  };
  topIntents: Array<{ intent: string; count: number; pct: number }>;
  modelVersion: string;
}

export async function fetchAnalytics(): Promise<AnalyticsData> {
  const res = await fetch(`${BACKEND_URL}/api/analytics`);
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function warmupBackend(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/warmup`, { method: 'POST' });
  if (!res.ok) throw new Error('Warmup failed');
  return res.json();
}

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchBankerSlots(date?: string): Promise<any[]> {
  const url = date ? `${BACKEND_URL}/api/banker-slots?date=${date}` : `${BACKEND_URL}/api/banker-slots`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch slots');
  return res.json();
}

export async function declineAppointment(appointmentId: string, reason?: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/appointments/${appointmentId}/decline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason || '' }),
  });
  if (!res.ok) throw new Error('Failed to decline appointment');
}
