import { useMemo } from 'react';
import { ChevronLeft, ChevronRight, X, ExternalLink, Calendar, Building2 } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAppointments } from '../hooks/useAppointments';

const CalendarView = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { appointments } = useAppointments();

  const selectedAppointment = useMemo(() => {
    const aptId = searchParams.get('appointmentId');
    if (aptId) {
      return appointments.find(a => a.id === aptId) || null;
    }
    return null;
  }, [searchParams]);

  const handleOpenAppointment = (apt: typeof appointments[0]) => {
    setSearchParams({ appointmentId: apt.id });
  };

  const handleCloseAppointment = () => {
    setSearchParams({});
  };

  const daysInMonth = 31;
  const startDayOffset = 4;
  const today = new Date();
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const blanks = Array.from({ length: startDayOffset }, (_, i) => i);

  const getAppointmentsForDay = (day: number) => {
    return appointments.filter(a => {
      const d = new Date(a.date);
      return d.getDate() === day;
    });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Calendar</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center bg-white rounded-lg border border-slate-200 p-1">
            <button className="p-1 hover:bg-slate-100 rounded"><ChevronLeft size={20} className="text-slate-500"/></button>
            <span className="px-4 font-semibold text-slate-700">Jan 2026</span>
            <button className="p-1 hover:bg-slate-100 rounded"><ChevronRight size={20} className="text-slate-500"/></button>
          </div>
          <button className="px-4 py-2 bg-[#DA1710] text-white text-sm font-medium rounded hover:bg-red-800 transition">
            New Appointment
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-7 border-b border-slate-200 bg-slate-50">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="py-3 px-4 text-xs font-semibold uppercase text-slate-500 text-center">
              {day}
            </div>
          ))}
        </div>
        
        <div className="grid grid-cols-7 auto-rows-[120px]">
          {blanks.map(b => (
            <div key={`blank-${b}`} className="bg-slate-50/50 border-b border-r border-slate-100"></div>
          ))}
          
          {days.map(day => {
            const dayAppointments = getAppointmentsForDay(day);
            return (
              <div key={day} className="border-b border-r border-slate-100 p-2 hover:bg-slate-50 transition relative group">
                <span className={`text-sm font-semibold ${day === today.getDate() ? 'bg-[#DA1710] text-white w-6 h-6 rounded-full flex items-center justify-center' : 'text-slate-700'}`}>
                  {day}
                </span>
                
                <div className="mt-2 space-y-1">
                  {dayAppointments.map(apt => (
                    <button 
                      key={apt.id}
                      onClick={() => handleOpenAppointment(apt)}
                      className="w-full text-left bg-red-50 hover:bg-red-100 text-[#DA1710] text-xs px-2 py-1 rounded border border-red-100 truncate block transition"
                    >
                      {apt.time} - {apt.customerName}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal */}
      {selectedAppointment && (
        <div 
          className="fixed inset-0 z-100 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
          onClick={handleCloseAppointment}
        >
          <div 
            className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col relative animate-in fade-in zoom-in duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              onClick={handleCloseAppointment}
              className="absolute top-4 right-4 p-2 bg-slate-100 hover:bg-slate-200 rounded-full z-10 transition"
            >
              <X size={20} className="text-slate-600" />
            </button>
            
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100">
              <div className="flex items-center gap-2 text-slate-500 text-sm font-medium mb-1">
                <Calendar size={16} />
                {new Date(selectedAppointment.date).toLocaleDateString('en-AU', { weekday: 'long', day: 'numeric', month: 'short' })} • {selectedAppointment.time} • {selectedAppointment.locationType}
              </div>
              <h2 className="text-xl font-bold text-slate-900">{selectedAppointment.type}</h2>
            </div>

            <div className="p-6 space-y-4">
              {/* Customer Card */}
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <div className="p-5 border-b border-slate-100">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-slate-200 rounded-full flex items-center justify-center text-lg font-bold text-slate-500">
                      {selectedAppointment.customerInitials}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-slate-900">{selectedAppointment.customerName}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {selectedAppointment.customerTenure || 'New Customer'}
                        </span>
                        {selectedAppointment.companyName && (
                          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                            <Building2 size={12} /> {selectedAppointment.companyName}
                          </span>
                        )}
                      </div>
                    </div>
                    {selectedAppointment.estimatedLoanSize && (
                      <div className="text-right">
                        <div className="text-xl font-bold text-[#DA1710]">{selectedAppointment.estimatedLoanSize}</div>
                        <div className="text-[10px] text-slate-400 uppercase">Est. Value</div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-4 bg-slate-50 grid grid-cols-3 gap-4 text-sm">
                  {selectedAppointment.location && (
                    <div>
                      <span className="text-slate-400 text-xs">Location</span>
                      <p className="text-slate-900 font-medium">{selectedAppointment.location}</p>
                    </div>
                  )}
                  {selectedAppointment.profession && (
                    <div>
                      <span className="text-slate-400 text-xs">Profession</span>
                      <p className="text-slate-900 font-medium">{selectedAppointment.profession}</p>
                    </div>
                  )}
                  {selectedAppointment.totalBankingValue && (
                    <div>
                      <span className="text-slate-400 text-xs">Banking Value</span>
                      <p className="text-slate-900 font-medium">{selectedAppointment.totalBankingValue}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Intent */}
              <div className="bg-slate-100 rounded-xl border border-slate-200 p-4">
                <div className="text-xs text-slate-00 uppercase font-bold mb-1">Intent</div>
                <div className="font-semibold text-slate-9600">{selectedAppointment.intent}</div>
                {selectedAppointment.aiNote && (
                  <p className="text-sm text-slate-500 mt-2">{selectedAppointment.aiNote}</p>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50">
              <button
                onClick={() => {
                  setSearchParams({});
                  navigate(`/appointment/${selectedAppointment.id}`);
                }}
                className="w-full py-2.5 bg-[#DA1710] text-white text-sm font-medium rounded-lg hover:bg-red-800 transition flex items-center justify-center gap-2"
              >
                <ExternalLink size={14} /> View Full Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CalendarView;
