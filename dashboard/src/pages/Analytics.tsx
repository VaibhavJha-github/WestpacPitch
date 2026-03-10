import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, Clock, Users, TrendingUp, CheckCircle, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { fetchAnalytics, type AnalyticsData } from '../lib/api';

const Analytics = () => {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    fetchAnalytics()
      .then(data => { setAnalytics(data); setIsLive(true); })
      .catch(() => setIsLive(false));
    const interval = setInterval(() => {
      fetchAnalytics().then(setAnalytics).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const liveMetrics = {
    activeCalls: analytics?.warm?.model_ready ? 1 : 0,
    inQueue: 0,
    avgWaitTime: analytics?.today?.avgTTFA || '0ms',
    availableBots: Object.values(analytics?.warm || {}).filter(Boolean).length,
    totalCapacity: 4,
  };

  const todayStats = {
    totalCalls: analytics?.today?.totalCalls || 0,
    completedAppointments: analytics?.today?.completedAppointments || 0,
    avgCallDuration: analytics?.today?.avgCallDuration || '0m 0s',
    conversionRate: analytics?.today?.conversionRate || 0,
    escalationRate: analytics?.today?.escalationCount || 0,
  };

  const sentimentBreakdown = [
    { label: 'Positive', value: analytics?.sentiment?.positive || 0, color: 'bg-green-500' },
    { label: 'Neutral', value: analytics?.sentiment?.neutral || 0, color: 'bg-slate-400' },
    { label: 'Anxious', value: analytics?.sentiment?.anxious || 0, color: 'bg-amber-500' },
    { label: 'Frustrated', value: analytics?.sentiment?.frustrated || 0, color: 'bg-red-500' },
  ];

  const topIntents = analytics?.topIntents || [];

  const hourlyVolume = [
    { hour: '8am', calls: 0 },
    { hour: '9am', calls: 0 },
    { hour: '10am', calls: todayStats.totalCalls },
    { hour: '11am', calls: 0 },
    { hour: '12pm', calls: 0 },
    { hour: '1pm', calls: 0 },
    { hour: '2pm', calls: 0 },
    { hour: '3pm', calls: 0 },
    { hour: '4pm', calls: 0 },
  ];

  const activeCalls: Array<{ id: number; callerId: string; elapsedMins: number }> = [];

  const formatElapsed = (mins: number) => {
    if (mins < 1) return '< 1 min';
    if (mins < 5) return '> 1 min';
    if (mins < 10) return '> 5 mins';
    return '> 10 mins';
  };

  const recentCalls = [
    { id: 1, customer: 'David L.', duration: '5:18', sentiment: 'Neutral', intent: 'First Home Buyer', outcome: 'Appointment booked' },
    { id: 2, customer: 'Emma W.', duration: '3:42', sentiment: 'Positive', intent: 'Refinance', outcome: 'Appointment booked' },
    { id: 3, customer: 'James K.', duration: '2:55', sentiment: 'Anxious', intent: 'Business Loan', outcome: 'Appointment booked' },
    { id: 4, customer: 'Lisa T.', duration: '4:02', sentiment: 'Frustrated', intent: 'Account Issue', outcome: 'Escalated to agent' },
    { id: 5, customer: 'Michael R.', duration: '1:23', sentiment: 'Neutral', intent: 'General Enquiry', outcome: 'Info provided' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-slate-500 hover:text-slate-700 mb-4 transition"
        >
          <ArrowLeft size={18} />
          <span className="text-sm font-medium">Back to Dashboard</span>
        </button>
        <h1 className="text-2xl font-bold text-slate-900">Callbot Analytics</h1>
        <p className="text-slate-500 mt-1">Real-time operations and performance metrics</p>
      </div>

      {/* ===== LIVE OPERATIONS ===== */}
      <section>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Live Operations</h2>
        
        {/* Status Bar */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-slate-700">System Online</span>
            </div>
            <div className="flex items-center gap-8 text-sm">
              <div className="flex items-center gap-2">
                <Phone size={16} className="text-green-600" />
                <span className="text-slate-600">{liveMetrics.activeCalls} active</span>
              </div>
              <div className="flex items-center gap-2">
                <Users size={16} className="text-amber-600" />
                <span className="text-slate-600">{liveMetrics.inQueue} queued</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-slate-500" />
                <span className="text-slate-600">~{liveMetrics.avgWaitTime} wait</span>
              </div>
              <div className="text-slate-300">|</div>
              <div className="text-slate-600">
                <span className="font-medium">{liveMetrics.availableBots}</span>/<span className="text-slate-400">{liveMetrics.totalCapacity}</span> bots available
              </div>
            </div>
          </div>
        </div>

        {/* Active Calls */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Phone size={14} className="text-green-600" />
              <h3 className="font-semibold text-slate-800">Active Calls</h3>
            </div>
            <span className="text-xs text-slate-400">{activeCalls.length} in progress</span>
          </div>
          <div className="divide-y divide-slate-100">
            {activeCalls.map(call => (
              <div key={call.id} className="px-5 py-3 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-900">{call.callerId}</span>
                <span className={`text-xs font-medium ${call.elapsedMins >= 10 ? 'text-amber-600' : 'text-slate-400'}`}>
                  {formatElapsed(call.elapsedMins)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== PERFORMANCE ===== */}
      <section>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Today's Performance</h2>
        
        <div className="grid grid-cols-12 gap-4">
          {/* Stats */}
          <div className="col-span-4 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="h-full flex flex-col justify-between">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500">Total Calls</span>
                <span className="text-md font-medium text-slate-900">{todayStats.totalCalls}</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500">Appointments</span>
                <span className="text-md font-medium text-slate-900">{todayStats.completedAppointments}</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500">Avg Duration</span>
                <span className="text-md font-medium text-slate-900">{todayStats.avgCallDuration}</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500">Conversion</span>
                <div className="flex items-center gap-1">
                  <span className="text-md font-medium text-green-600">{todayStats.conversionRate}%</span>
                  <TrendingUp size={14} className="text-green-600" />
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500">Escalation Rate</span>
                <span className="text-md font-medium text-slate-900">{todayStats.escalationRate}%</span>
              </div>
            </div>
          </div>

          {/* Hourly Chart */}
          <div className="col-span-8 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="font-semibold text-slate-800">Call Volume by Hour</h3>
            </div>
            <div className="p-5">
              <div className="flex gap-4">
                {/* Y-axis */}
                <div className="flex flex-col justify-between w-6 text-right" style={{ height: '120px' }}>
                  <span className="text-xs text-slate-400">45</span>
                  <span className="text-xs text-slate-400">30</span>
                  <span className="text-xs text-slate-400">15</span>
                  <span className="text-xs text-slate-400">0</span>
                </div>
                {/* Bars container */}
                <div className="flex-1">
                  <div className="flex items-end gap-2" style={{ height: '120px' }}>
                    {hourlyVolume.map((h, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
                        <div 
                          className="w-full max-w-10 bg-[#DA1710] rounded-t hover:bg-red-700 transition-colors animate-bar-rise"
                          style={{ 
                            height: `${Math.max((h.calls / 45) * 120, 2)}px`,
                            animationDelay: `${i * 40}ms`
                          }}
                        ></div>
                      </div>
                    ))}
                  </div>
                  {/* X-axis */}
                  <div className="flex gap-2 mt-2 border-t border-slate-100 pt-2">
                    {hourlyVolume.map((h, i) => (
                      <div key={i} className="flex-1 text-center text-xs text-slate-500">{h.hour}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== INSIGHTS & HISTORY ===== */}
      <section>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Insights</h2>
        
        <div className="grid grid-cols-12 gap-4">
          {/* Recent Completed Calls */}
          <div className="col-span-8 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="font-semibold text-slate-800">Recent Completed Calls</h3>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="text-left px-5 py-2.5 text-xs font-medium uppercase text-slate-500">Customer</th>
                  <th className="text-left px-5 py-2.5 text-xs font-medium uppercase text-slate-500">Duration</th>
                  <th className="text-left px-5 py-2.5 text-xs font-medium uppercase text-slate-500">Sentiment</th>
                  <th className="text-left px-5 py-2.5 text-xs font-medium uppercase text-slate-500">Intent</th>
                  <th className="text-left px-5 py-2.5 text-xs font-medium uppercase text-slate-500">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentCalls.map(call => (
                  <tr key={call.id}>
                    <td className="px-5 py-2.5 font-medium text-slate-900">{call.customer}</td>
                    <td className="px-5 py-2.5 text-slate-600 font-mono text-xs">{call.duration}</td>
                    <td className="px-5 py-2.5">
                      <span className={`text-xs font-medium ${
                        call.sentiment === 'Positive' ? 'text-green-600' :
                        call.sentiment === 'Anxious' ? 'text-amber-600' :
                        call.sentiment === 'Frustrated' ? 'text-red-600' :
                        'text-slate-500'
                      }`}>{call.sentiment}</span>
                    </td>
                    <td className="px-5 py-2.5 text-slate-600">{call.intent}</td>
                    <td className="px-5 py-2.5">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                        call.outcome.includes('booked') ? 'text-green-600' :
                        call.outcome.includes('Escalated') ? 'text-red-600' :
                        'text-slate-600'
                      }`}>
                        {call.outcome.includes('booked') && <CheckCircle size={12} />}
                        {call.outcome.includes('Escalated') && <AlertCircle size={12} />}
                        {call.outcome}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right column: Sentiment + Intents */}
          <div className="col-span-4 space-y-4">
            {/* Sentiment */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Sentiment Distribution</h3>
              <div className="space-y-2.5">
                {sentimentBreakdown.map((s, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600">{s.label}</span>
                      <span className="font-medium text-slate-700">{s.value}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div className={`h-full ${s.color} rounded-full`} style={{ width: `${s.value}%` }}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Intents */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Top Intents</h3>
              <div className="space-y-2">
                {topIntents.slice(0, 4).map((intent, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-slate-600">{intent.intent}</span>
                    <span className="text-xs text-slate-400">{intent.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== SYSTEM ===== */}
      <section>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">System</h2>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
          <div className="flex items-center gap-12 text-sm">
            <div>
              <span className="text-slate-500">Uptime</span>
              <span className="ml-2 font-medium text-green-600">99.98%</span>
            </div>
            <div>
              <span className="text-slate-500">Latency</span>
              <span className="ml-2 font-medium text-slate-900">142ms</span>
            </div>
            <div>
              <span className="text-slate-500">Error Rate</span>
              <span className="ml-2 font-medium text-slate-900">0.02%</span>
            </div>
            <div>
              <span className="text-slate-500">Escalation Rate</span>
              <span className="ml-2 font-medium text-slate-900">{todayStats.escalationRate}%</span>
            </div>
            <div>
              <span className="text-slate-500">Model</span>
              <span className="ml-2 font-medium text-slate-900">{analytics?.modelVersion || 'Qwen2.5-14B-AWQ'}</span>
            </div>
            <div>
              <span className="text-slate-500">Data</span>
              {isLive ? (
                <span className="ml-2 inline-flex items-center gap-1 font-medium text-green-600"><Wifi size={12} /> Live</span>
              ) : (
                <span className="ml-2 inline-flex items-center gap-1 font-medium text-slate-400"><WifiOff size={12} /> Demo</span>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Analytics;
