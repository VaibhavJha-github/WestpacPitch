import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Briefcase, Sparkles, Building2, CheckCircle2, XCircle, Clock, MessageSquare } from 'lucide-react';
import { fetchAppointment, acceptSlot, declineAppointment, fetchBankerSlots } from '../lib/api';
import { appointments as mockAppointments } from '../data/mockData';
import type { Appointment } from '../data/mockData';

const AppointmentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [appointment, setAppointment] = useState<Appointment | undefined>(
    mockAppointments.find(a => a.id === id)
  );
  const [accepting, setAccepting] = useState(false);
  const [declining, setDeclining] = useState(false);
  const [actionDone, setActionDone] = useState<'accepted' | 'declined' | null>(null);
  const [smsStatus, setSmsStatus] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchAppointment(id).then(setAppointment).catch(() => {});
    }
  }, [id]);

  const handleAccept = async () => {
    if (!appointment || !id) return;
    setAccepting(true);
    try {
      // Use preferred_slot_id if available, otherwise fetch first available slot
      const slotId = (appointment as any).preferredSlotId || (appointment as any).preferred_slot_id;
      if (slotId) {
        await acceptSlot(id, slotId);
      } else {
        // Fetch slots and use the first one
        const slots = await fetchBankerSlots();
        if (slots.length > 0) {
          await acceptSlot(id, slots[0].id);
        }
      }
      setActionDone('accepted');
      setSmsStatus('Confirmation SMS sent to customer. Cross-sell SMS will follow in 10 seconds.');
      // Refresh appointment data
      const updated = await fetchAppointment(id);
      setAppointment(updated);
    } catch (e) {
      console.error('Accept failed:', e);
    } finally {
      setAccepting(false);
    }
  };

  const handleDecline = async () => {
    if (!id) return;
    setDeclining(true);
    try {
      await declineAppointment(id);
      setActionDone('declined');
      const updated = await fetchAppointment(id);
      setAppointment(updated);
    } catch (e) {
      console.error('Decline failed:', e);
    } finally {
      setDeclining(false);
    }
  };

  if (!appointment) {
    return (
      <div className="p-8 text-center bg-white rounded-lg shadow-sm border border-slate-200">
        <h2 className="text-xl font-bold text-slate-900">Appointment Not Found</h2>
        <Link to="/" className="text-[#DA1710] hover:underline mt-4 inline-block">Return to Dashboard</Link>
      </div>
    );
  }

  const formattedDate = new Date(appointment.date).toLocaleDateString('en-AU', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  });

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'Positive': return { text: 'text-green-600', bg: 'bg-green-500' };
      case 'Anxious': return { text: 'text-amber-600', bg: 'bg-amber-500' };
      case 'Frustrated': return { text: 'text-red-600', bg: 'bg-red-500' };
      default: return { text: 'text-slate-600', bg: 'bg-slate-400' };
    }
  };

  const sentimentColors = getSentimentColor(appointment.sentiment);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex gap-4">
          <div>
            <div className="flex items-center mb-2 gap-4">
              <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-2 text-slate-500 hover:text-slate-700 transition"
              >
                <ArrowLeft size={18} />
              </button>
              <h1 className="text-2xl font-bold text-slate-900">{appointment.type}</h1>
            </div>
            <div className="flex items-center gap-2 text-slate-500 text-sm font-medium">
              {formattedDate} • {appointment.time} • {appointment.locationType}
            </div>
          </div>
        </div>
        <div className="flex gap-3 items-center">
          {/* Status badge */}
          {appointment.status === 'Pending' && !actionDone && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
              <Clock size={12} /> Pending Approval
            </span>
          )}
          {(appointment.status === 'Upcoming' || actionDone === 'accepted') && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">
              <CheckCircle2 size={12} /> Confirmed
            </span>
          )}
          {(appointment.status === 'Cancelled' || actionDone === 'declined') && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">
              <XCircle size={12} /> Declined
            </span>
          )}

          {/* Action buttons for Pending appointments */}
          {appointment.status === 'Pending' && !actionDone && (
            <>
              <button
                onClick={handleDecline}
                disabled={declining}
                className="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded-sm hover:bg-slate-50 disabled:opacity-50"
              >
                {declining ? 'Declining...' : 'Decline'}
              </button>
              <button
                onClick={handleAccept}
                disabled={accepting}
                className="px-6 py-2 bg-green-600 text-sm text-white font-medium rounded-sm shadow-sm hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
              >
                {accepting ? 'Accepting...' : <>Accept Booking <CheckCircle2 size={16} /></>}
              </button>
            </>
          )}

          {/* Existing buttons for confirmed appointments */}
          {(appointment.status === 'Upcoming' || actionDone === 'accepted') && (
            <>
              <button className="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded-sm hover:bg-slate-50">
                Reschedule
              </button>
              {(appointment.locationType === 'Video chat' || appointment.locationType === 'Phone') && (
                <button className="px-6 py-2 bg-[#DA1710] text-sm text-white font-medium rounded-sm shadow-sm hover:bg-red-800 flex items-center gap-2">
                  Launch Meeting <ArrowRight size={16} />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* SMS notification banner */}
      {smsStatus && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl animate-in fade-in duration-500">
          <MessageSquare size={18} className="text-green-600 shrink-0" />
          <p className="text-sm text-green-800">{smsStatus}</p>
        </div>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* LEFT COLUMN: Customer + Intent + Readiness */}
        <div className="col-span-5 space-y-6">
          {/* Combined Customer & Intent Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            {/* Customer Header */}
            <div className="p-6 border-b border-slate-100">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-slate-200 rounded-full flex items-center justify-center text-lg font-bold text-slate-500">
                  {appointment.customerInitials}
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-bold text-slate-900">{appointment.customerName}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {appointment.customerTenure ? `${appointment.customerTenure}` : 'New Customer'}
                    </span>
                    {appointment.companyName && (
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                        <Building2 size={12} /> {appointment.companyName}
                      </span>
                    )}
                  </div>
                </div>
                {appointment.estimatedLoanSize && (
                  <div className="text-right">
                    <div className="text-2xl font-bold text-[#DA1710]">{appointment.estimatedLoanSize}</div>
                    <div className="text-[10px] text-slate-400 uppercase font-bold">Est. Value</div>
                  </div>
                )}
              </div>
            </div>

            {/* Customer Details Grid */}
            <div className="p-4 bg-slate-50 grid grid-cols-2 gap-3 text-sm">
              {appointment.age && appointment.location && (
                <div>
                  <span className="text-slate-400 text-xs">Location</span>
                  <p className="text-slate-900 font-medium">{appointment.location}</p>
                </div>
              )}
              {appointment.profession && (
                <div>
                  <span className="text-slate-400 text-xs">Profession</span>
                  <p className="text-slate-900 font-medium">{appointment.profession}</p>
                </div>
              )}
              {appointment.totalBankingValue && (
                <div>
                  <span className="text-slate-400 text-xs">Banking Value</span>
                  <p className="text-slate-900 font-medium">{appointment.totalBankingValue}</p>
                </div>
              )}
              {appointment.currentLender && (
                <div>
                  <span className="text-slate-400 text-xs">Current Lender</span>
                  <p className="text-slate-900 font-medium">{appointment.currentLender}</p>
                </div>
              )}
            </div>

          </div>

          {/* Intent Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <div className="text-xs text-slate-400 uppercase font-bold mb-1">Intent</div>
            <div className="font-semibold text-slate-900">{appointment.intent}</div>
            {appointment.reasonForLeaving && (
              <div className="text-sm text-slate-500 mt-1">Reason: {appointment.reasonForLeaving}</div>
            )}
          </div>

          {/* Collected Information */}
          {appointment.collectedData && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100">
                <h3 className="font-bold text-slate-800 text-sm">Collected Information</h3>
              </div>
              <div className="p-5">
                <ul className="space-y-2 text-sm">
                  {appointment.collectedData.map((item, i) => (
                    <li key={i} className="flex justify-between">
                      <span className="text-slate-500">{item.label}</span>
                      <span className="text-slate-900 font-medium">{item.value || '—'}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Recommended Strategy */}
          {appointment.recommendedStrategy && (
            <div className="bg-slate-100 border border-slate-200 p-4 rounded-xl flex gap-3 shadow-sm">
              <div className="mt-0.5"><Briefcase className="text-slate-500" size={20} /></div>
              <div>
                <h4 className="font-bold text-slate-800 text-sm">{appointment.recommendedStrategy.title}</h4>
                <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                  {appointment.recommendedStrategy.description}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Transcript with AI Summary */}
        <div className="col-span-7">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col max-h-200">
            {/* Transcript Header */}
            <div className="px-5 py-3 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-800">Call Transcript</h3>
                <p className="text-xs text-slate-500 mt-0.5">{appointment.transcript.length} messages</p>
              </div>
              {/* Sentiment Badge */}
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium ${sentimentColors.text}`}>{appointment.sentiment}</span>
                <div className="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className={`h-full ${sentimentColors.bg}`} style={{ width: `${appointment.sentimentScore}%` }}></div>
                </div>
              </div>
            </div>

            {/* AI Summary */}
            <div className="p-4 border-b border-slate-200 bg-slate-50">
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-full bg-white border border-slate-200 flex items-center justify-center shrink-0">
                  <Sparkles size={14} className="text-[#DA1710]" />
                </div>
                <div className="flex-1">
                  <div className="text-xs font-medium text-slate-500 uppercase mb-1">AI Summary</div>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {appointment.aiNote}
                    {appointment.sentimentNote && (
                      <span className="text-slate-500"> — {appointment.sentimentNote}</span>
                    )}
                  </p>
                </div>
              </div>
            </div>

            {/* Transcript Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {appointment.transcript.map(msg => (
                <div key={msg.id} className={`flex flex-col ${msg.sender === 'Bot' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[80%] p-3 rounded-xl text-sm ${
                    msg.sender === 'Customer' 
                      ? 'bg-slate-100 text-slate-800 rounded-tl-none'
                      : 'bg-red-50 text-slate-800 rounded-br-sm border border-red-100'
                    
                  }`}>
                    <p>{msg.text}</p>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1 px-1">
                    {msg.sender} • {msg.timestamp}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AppointmentDetail;
