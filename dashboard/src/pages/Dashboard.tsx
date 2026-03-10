import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart3, Wifi, WifiOff } from "lucide-react";
import AppointmentCard from "../components/AppointmentCard";
import TranscriptPanel from "../components/TranscriptPanel";
import { useAppointments } from "../hooks/useAppointments";

const Dashboard = () => {
  const navigate = useNavigate();
  const { appointments, isLive, loading, error } = useAppointments();
  const [selectedAppointmentId, setSelectedAppointmentId] =
    useState<string>("");

  const effectiveSelectedId =
    selectedAppointmentId || (appointments[0]?.id ?? "");
  const selectedAppointment =
    appointments.find((a) => a.id === effectiveSelectedId) || appointments[0];

  // Group appointments by date
  const groupedAppointments = useMemo(() => {
    const groups: Record<string, typeof appointments> = {};

    appointments.forEach((apt) => {
      if (!groups[apt.date]) {
        groups[apt.date] = [];
      }
      groups[apt.date].push(apt);
    });

    // Sort dates and return as array of [date, appointments]
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [appointments]);

  const formatDateHeader = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const isToday = date.toDateString() === today.toDateString();
    const isTomorrow = date.toDateString() === tomorrow.toDateString();

    const formatted = date.toLocaleDateString("en-AU", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });

    if (isToday) return `Today — ${formatted}`;
    if (isTomorrow) return `Tomorrow — ${formatted}`;
    return formatted;
  };

  // Find first appointment overall for "Next" badge
  const firstAppointmentId = appointments[0]?.id;

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Scheduled Appointments
          </h1>
          <p className="text-slate-500 mt-1 flex items-center gap-2">
            You have {appointments.length} meetings booked via Westpac AI
            Assistant.
            {isLive ? (
              <span className="inline-flex items-center gap-1 text-xs text-green-600">
                <Wifi size={12} /> Live
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                <WifiOff size={12} /> Demo
              </span>
            )}
          </p>
          {error && <p className="text-xs text-amber-600 mt-1">{error}</p>}
        </div>
      </div>

      {loading && appointments.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          Loading live appointments...
        </div>
      )}

      {!loading && appointments.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No appointments yet. Complete a live call and booking to populate this
          dashboard.
        </div>
      )}

      {/* Content Grid */}
      {appointments.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Grouped List */}
          <div className="lg:col-span-2 space-y-6">
            {groupedAppointments.map(([date, dateAppointments]) => (
              <div key={date}>
                <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  {formatDateHeader(date)}
                </h2>
                <div className="space-y-3">
                  {dateAppointments.map((apt) => (
                    <AppointmentCard
                      key={apt.id}
                      appointment={apt}
                      isNext={apt.id === firstAppointmentId}
                      isSelected={selectedAppointmentId === apt.id}
                      onClick={() => setSelectedAppointmentId(apt.id)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Right: Details */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 mt-8">
              <TranscriptPanel
                appointment={selectedAppointment}
                previewMode={true}
              />
            </div>
          </div>
        </div>
      )}

      {/* Analytics Link */}
      <div className="mt-12 pt-6 border-t border-slate-200">
        <button
          onClick={() => navigate("/analytics")}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-600 text-sm transition"
        >
          <BarChart3 size={16} />
          <span>View Callbot Analytics</span>
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
