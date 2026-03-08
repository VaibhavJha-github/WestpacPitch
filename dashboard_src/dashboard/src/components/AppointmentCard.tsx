import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Phone, Building, Car } from 'lucide-react';
import type { Appointment } from '../data/mockData';

interface AppointmentCardProps {
  appointment: Appointment;
  isSelected?: boolean;
  onClick?: () => void;
  isNext?: boolean;
}

const AppointmentCard: React.FC<AppointmentCardProps> = ({ 
  appointment, 
  isSelected = false, 
  onClick,
  isNext = false
}) => {
  const navigate = useNavigate();

  const sentimentColor = 
    appointment.sentiment === 'Positive' ? 'text-green-700' :
    appointment.sentiment === 'Anxious' ? 'text-yellow-700' :
    'text-slate-700';
    
  // Helper to determine border color based on state
  const borderColor = isSelected 
    ? 'border-l-4 border-l-[#DA1710] border-y border-r border-slate-200' 
    : 'border border-slate-200';

  return (
    <div 
      onClick={onClick}
      className={`bg-white rounded-xl shadow-sm p-6 cursor-pointer hover:shadow-md transition-all ${borderColor}`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
			{/* Show "Next Up" badge only if it's the very next one */}
            {isNext && (
              <span className="bg-red-50 text-[#DA1710] px-2 py-1 rounded text-xs font-bold uppercase tracking-wide">
                Next Up: {new Date(appointment.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}, {appointment.time}
              </span>
            )}
            {!isNext && (
                 <span className="text-slate-500 text-sm font-medium">
                  {new Date(appointment.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} • {appointment.time}
                </span>
            )}
            <span className="text-slate-400 text-sm flex items-center">
              {appointment.locationType === 'In-branch' && <Building size={14} className="mr-1" />}
              {appointment.locationType === 'Mobile lender visit' && <Car size={14} className="mr-1" />}
              {appointment.locationType === 'Phone' && <Phone size={14} className="mr-1" />}
              {appointment.locationType === 'Video chat' && <Video size={14} className="mr-1" />}
              {appointment.locationType}
            </span>
          </div>
          <h3 
            onClick={(e) => {
              if (isSelected) {
                e.stopPropagation();
                navigate(`/appointment/${appointment.id}`);
              }
            }}
            className={`text-lg font-bold text-slate-900 ${isSelected ? 'hover:text-[#DA1710] cursor-pointer transition' : ''}`}
          >
            {appointment.type}
          </h3>
          <p className="text-slate-600 mt-1">
            with <span className="font-medium">{appointment.customerName}</span>
          </p>

          <div className="mt-4 flex gap-4">
            <div className="bg-slate-50 px-3 py-2 rounded border border-slate-100">
              <div className="text-xs text-slate-500 uppercase font-semibold">
                AI Sentiment
              </div>
              <div className={`text-sm font-medium flex items-center gap-1 ${sentimentColor}`}>
                {appointment.sentiment} ({appointment.sentimentScore}%)
              </div>
            </div>
            <div className="bg-slate-50 px-3 py-2 rounded border border-slate-100">
              <div className="text-xs text-slate-500 uppercase font-semibold">
                Detected Intent
              </div>
              <div className="text-sm font-medium text-slate-700">
                {appointment.intent}
              </div>
            </div>
          </div>
        </div>
        
        {/* Action Buttons (Visible mostly on hover or selected, but we keep simple) */}
        <div className="flex flex-col gap-2 ml-4">
            {isNext && new Date(appointment.date).toDateString() === new Date().toDateString() && (
                 <button className="px-4 py-2 bg-[#DA1710] text-white text-sm font-medium rounded hover:bg-red-800 transition whitespace-nowrap">
                  Join Meeting
                </button>
            )}
            <button 
                onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/appointment/${appointment.id}`);
                }}
                className="text-[#DA1710] hover:bg-red-50 px-3 py-1 text-sm font-medium rounded transition whitespace-nowrap"
            >
               View Details
            </button>
        </div>
      </div>
    </div>
  );
};

export default AppointmentCard;
