import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, MapPin, Calendar, TrendingUp, Search } from 'lucide-react';
import { useClients } from '../hooks/useClients';

const Clients = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const { clients: allClients } = useClients();
  
  const clients = useMemo(() => {
    if (!searchQuery.trim()) return allClients;
    const query = searchQuery.toLowerCase();
    return allClients.filter(client => 
      client.name.toLowerCase().includes(query) ||
      client.companyName?.toLowerCase().includes(query) ||
      client.profession?.toLowerCase().includes(query) ||
      client.location?.toLowerCase().includes(query)
    );
  }, [allClients, searchQuery]);

  const getSentimentColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 bg-emerald-50';
    if (score >= 60) return 'text-amber-600 bg-amber-50';
    return 'text-red-600 bg-red-50';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-AU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div>
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Clients</h1>
          <p className="text-slate-500 mt-1">
            {clients.length} customer{clients.length !== 1 ? 's' : ''} you've interacted with via AI Assistant.
          </p>
        </div>
        <div className="relative bg-white/75">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search clients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-4 py-2 w-64 border border-slate-300 rounded-lg text-sm focus:outline-none"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-6 py-4 text-xs font-semibold uppercase text-slate-500">Client</th>
              <th className="text-left px-6 py-4 text-xs font-semibold uppercase text-slate-500">Details</th>
              <th className="text-left px-6 py-4 text-xs font-semibold uppercase text-slate-500">Last Contact</th>
              <th className="text-left px-6 py-4 text-xs font-semibold uppercase text-slate-500">Appointments</th>
              <th className="text-left px-6 py-4 text-xs font-semibold uppercase text-slate-500">Sentiment</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {clients.map(client => (
              <tr
                key={client.id}
                onClick={() => navigate(`/clients/${client.id}`)}
                className="hover:bg-slate-50 cursor-pointer transition"
              >
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center text-sm font-bold text-slate-500">
                      {client.initials}
                    </div>
                    <div>
                      <div className="font-semibold text-slate-900">{client.name}</div>
                      {client.companyName && (
                        <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                          <Building2 size={12} />
                          {client.companyName}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-slate-600">
                    {client.profession && <div>{client.profession}</div>}
                    {client.location && (
                      <div className="flex items-center gap-1 text-slate-400 mt-0.5">
                        <MapPin size={12} />
                        {client.location}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1.5 text-sm text-slate-600">
                    <Calendar size={14} className="text-slate-400" />
                    {formatDate(client.lastContactDate)}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-sm font-medium text-slate-700">
                    {client.totalAppointments}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(client.averageSentiment)}`}>
                    <TrendingUp size={12} />
                    {Math.round(client.averageSentiment)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Clients;
