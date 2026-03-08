import { appointments } from './mockData';
import type { Appointment } from './mockData';

export interface Client {
  id: string;
  name: string;
  initials: string;
  companyName?: string;
  location?: string;
  profession?: string;
  tenure?: string;
  totalBankingValue?: string;
  appointments: Appointment[];
  lastContactDate: string;
  totalAppointments: number;
  averageSentiment: number;
}

export const getClientsFromAppointments = (): Client[] => {
  const clientMap = new Map<string, Client>();

  appointments.forEach(apt => {
    const key = apt.customerName;
    
    if (clientMap.has(key)) {
      const existing = clientMap.get(key)!;
      existing.appointments.push(apt);
      existing.totalAppointments++;
      existing.averageSentiment = 
        (existing.averageSentiment * (existing.totalAppointments - 1) + apt.sentimentScore) / existing.totalAppointments;
      if (apt.date > existing.lastContactDate) {
        existing.lastContactDate = apt.date;
      }
    } else {
      clientMap.set(key, {
        id: `client-${apt.id}`,
        name: apt.customerName,
        initials: apt.customerInitials,
        companyName: apt.companyName,
        location: apt.location,
        profession: apt.profession,
        tenure: apt.customerTenure,
        totalBankingValue: apt.totalBankingValue,
        appointments: [apt],
        lastContactDate: apt.date,
        totalAppointments: 1,
        averageSentiment: apt.sentimentScore,
      });
    }
  });

  return Array.from(clientMap.values()).sort((a, b) => 
    b.lastContactDate.localeCompare(a.lastContactDate)
  );
};

export const getClientById = (clientId: string): Client | undefined => {
  return getClientsFromAppointments().find(c => c.id === clientId);
};
