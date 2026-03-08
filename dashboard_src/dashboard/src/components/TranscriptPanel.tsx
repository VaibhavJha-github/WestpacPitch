import React from 'react';
import { FileText, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { Appointment } from '../data/mockData';

interface TranscriptPanelProps {
  appointment: Appointment | null;
  previewMode?: boolean;
  hideButton?: boolean;
}

const TranscriptPanel: React.FC<TranscriptPanelProps> = ({ appointment, previewMode = false, hideButton = false }) => {
  const navigate = useNavigate();

  if (!appointment) {
    return (
      <div className="bg-white rounded-xl shadow-2xs border border-slate-200 flex flex-col h-full min-h-100 items-center justify-center text-slate-400">
        <FileText size={48} className="opacity-20 mb-4" />
        <p>Select an appointment to view details</p>
      </div>
    );
  }

  const displayedTranscript = previewMode ? appointment.transcript.slice(0, 4) : appointment.transcript;

  return (
    <div className="bg-white rounded-xl shadow-xs border border-slate-200 flex flex-col h-150">
      <div className="p-5 border-b border-slate-100">
        <h3 className="font-bold text-slate-800">
          {previewMode ? 'Transcript Preview' : 'Call Transcript'}
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          {appointment.transcript.length} messages from callbot session
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-white">
        <div className="flex flex-col gap-3 text-sm">
          {displayedTranscript.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.sender === 'Bot' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[85%] p-3 rounded-lg text-sm ${
                msg.sender === 'Bot' 
                  ? 'bg-red-50 text-slate-800 rounded-tr-none border border-red-100' 
                  : 'bg-slate-100 text-slate-800 rounded-tl-none'
              }`}>
                <p>{msg.text}</p>
              </div>
              <span className="text-[10px] text-slate-400 mt-1">{msg.sender} • {msg.timestamp}</span>
            </div>
          ))}
          {previewMode && appointment.transcript.length > 4 && (
            <div className="text-center text-sm text-slate-400 italic py-2">
              + {appointment.transcript.length - 4} more messages...
            </div>
          )}
        </div>
      </div>

      {previewMode && !hideButton && (
        <div className="p-4 border-t border-slate-100 bg-white rounded-b-xl">
          <button 
            onClick={() => navigate(`/appointment/${appointment.id}`)}
            className="w-full py-2 bg-[#DA1710] text-white text-sm font-medium rounded hover:bg-red-800 transition flex items-center justify-center gap-2"
          >
            <ExternalLink size={14} /> View Full Details
          </button>
        </div>
      )}
    </div>
  );
};

export default TranscriptPanel;
