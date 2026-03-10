import { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, Calendar, MessageSquare } from 'lucide-react';
import { getClientById } from '../data/clientsData';

const ClientProfile = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const client = useMemo(() => getClientById(id || ''), [id]);

  if (!client) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Client not found</p>
        <button onClick={() => navigate('/clients')} className="mt-4 text-[#DA1710] hover:underline">
          Back to Clients
        </button>
      </div>
    );
  }

  const getSentimentStyle = (score: number) => {
    if (score >= 80) return { text: 'text-green-600', bg: 'bg-green-500', label: 'Positive' };
    if (score >= 60) return { text: 'text-amber-600', bg: 'bg-amber-500', label: 'Neutral' };
    return { text: 'text-red-600', bg: 'bg-red-500', label: 'Needs Attention' };
  };

  const sentimentStyle = getSentimentStyle(client.averageSentiment);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-AU', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const allCollectedData = client.appointments
    .flatMap(apt => apt.collectedData || [])
    .filter((item, index, self) => 
      index === self.findIndex(t => t.label === item.label)
    );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/clients')}
          className="flex items-center gap-2 text-slate-500 hover:text-slate-700 mb-4 transition"
        >
          <ArrowLeft size={18} />
          <span className="text-sm font-medium">Back to Clients</span>
        </button>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* LEFT COLUMN: Client Info */}
        <div className="col-span-5 space-y-6">
          {/* Customer Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-slate-200 rounded-full flex items-center justify-center text-lg font-bold text-slate-500">
                  {client.initials}
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-bold text-slate-900">{client.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {client.tenure ? `${client.tenure}` : 'New Customer'}
                    </span>
                    {client.companyName && (
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                        <Building2 size={12} /> {client.companyName}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Details Grid */}
            <div className="p-4 bg-slate-50 grid grid-cols-2 gap-3 text-sm">
              {client.location && (
                <div>
                  <span className="text-slate-400 text-xs">Location</span>
                  <p className="text-slate-900 font-medium">{client.location}</p>
                </div>
              )}
              {client.profession && (
                <div>
                  <span className="text-slate-400 text-xs">Profession</span>
                  <p className="text-slate-900 font-medium">{client.profession}</p>
                </div>
              )}
              {client.totalBankingValue && (
                <div>
                  <span className="text-slate-400 text-xs">Banking Value</span>
                  <p className="text-slate-900 font-medium">{client.totalBankingValue}</p>
                </div>
              )}
            </div>
          </div>

          {/* Sentiment Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <div className="flex justify-between items-center">
              <div>
                <div className="text-xs text-slate-400 uppercase font-bold mb-1">Avg Sentiment</div>
                <div className={`text-sm font-medium ${sentimentStyle.text}`}>{sentimentStyle.label}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium ${sentimentStyle.text}`}>{Math.round(client.averageSentiment)}%</span>
                <div className="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className={`h-full ${sentimentStyle.bg}`} style={{ width: `${client.averageSentiment}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Collected Information */}
          {allCollectedData.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100">
                <h3 className="font-bold text-slate-800 text-sm">Collected Information</h3>
              </div>
              <div className="p-5">
                <ul className="space-y-2 text-sm">
                  {allCollectedData.map((item, i) => (
                    <li key={i} className="flex justify-between">
                      <span className="text-slate-500">{item.label}</span>
                      <span className="text-slate-900 font-medium">{item.value || '—'}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Interaction History */}
        <div className="col-span-7">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
              <h3 className="font-bold text-slate-800">Interaction History</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {client.totalAppointments} appointment{client.totalAppointments !== 1 ? 's' : ''} recorded
              </p>
            </div>

            <div className="divide-y divide-slate-100">
              {client.appointments.map(apt => (
                <div
                  key={apt.id}
                  onClick={() => navigate(`/appointment/${apt.id}`)}
                  className="p-4 hover:bg-slate-50 cursor-pointer transition"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-semibold text-slate-900">{apt.type}</div>
                      <div className="flex items-center gap-3 text-sm text-slate-500 mt-1">
                        <span className="flex items-center gap-1">
                          <Calendar size={14} />
                          {formatDate(apt.date)}
                        </span>
                        <span>{apt.time}</span>
                        <span className="text-slate-300">•</span>
                        <span>{apt.locationType}</span>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      apt.status === 'Completed' ? 'bg-emerald-50 text-emerald-700' :
                      apt.status === 'Upcoming' ? 'bg-blue-50 text-blue-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {apt.status}
                    </span>
                  </div>

                  <div className="text-sm text-slate-600 mb-2">{apt.intent}</div>

                  {apt.aiNote && (
                    <div className="flex items-start gap-2 bg-slate-50 rounded-lg p-3 text-sm">
                      <MessageSquare size={14} className="text-slate-400 mt-0.5 shrink-0" />
                      <p className="text-slate-600 line-clamp-2">{apt.aiNote}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientProfile;
