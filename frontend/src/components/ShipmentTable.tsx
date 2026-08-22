import type { Shipment } from '../types';
import { RISK_COLORS } from '../types';
import { Thermometer, Clock, AlertTriangle } from 'lucide-react';

interface Props {
  shipments: Shipment[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide"
      style={{
        color: RISK_COLORS[level] || '#94a3b8',
        background: `${RISK_COLORS[level] || '#94a3b8'}20`,
        border: `1px solid ${RISK_COLORS[level] || '#94a3b8'}40`,
      }}
    >
      {level}
    </span>
  );
}

export default function ShipmentTable({ shipments, selectedId, onSelect }: Props) {
  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="px-4 py-2.5 border-b flex items-center gap-2" style={{ borderColor: 'rgba(148,163,184,0.1)' }}>
        <Package size={14} className="text-blue-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Active Shipments
        </span>
      </div>
      <div className="overflow-auto" style={{ maxHeight: '240px' }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 uppercase tracking-wider border-b" style={{ borderColor: 'rgba(148,163,184,0.08)' }}>
              <th className="text-left px-3 py-2 font-medium">Shipment</th>
              <th className="text-left px-3 py-2 font-medium">Product</th>
              <th className="text-left px-3 py-2 font-medium">Temp</th>
              <th className="text-left px-3 py-2 font-medium">ETA</th>
              <th className="text-left px-3 py-2 font-medium">Risk</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {shipments.map((s) => (
              <tr
                key={s.shipmentId}
                onClick={() => onSelect(s.shipmentId)}
                className="cursor-pointer transition-colors border-b"
                style={{
                  borderColor: 'rgba(148,163,184,0.06)',
                  background: selectedId === s.shipmentId
                    ? 'rgba(59,130,246,0.1)'
                    : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (selectedId !== s.shipmentId)
                    e.currentTarget.style.background = 'rgba(148,163,184,0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background =
                    selectedId === s.shipmentId
                      ? 'rgba(59,130,246,0.1)'
                      : 'transparent';
                }}
              >
                <td className="px-3 py-2">
                  <div className="font-mono font-semibold text-slate-200">
                    {s.shipmentId}
                  </div>
                </td>
                <td className="px-3 py-2">
                  <div className="text-slate-300">{s.productType}</div>
                  <div className="text-xs text-slate-500">{s.productName}</div>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1 font-mono">
                    <Thermometer size={12} style={{ color: RISK_COLORS[s.riskLevel] }} />
                    <span className="text-slate-200">{s.temperature.toFixed(1)}°C</span>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1">
                    <Clock size={12} className="text-slate-500" />
                    <span className="text-slate-300 font-mono">{s.etaMinutes} min</span>
                  </div>
                  {s.delayMinutes > 0 && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <AlertTriangle size={10} className="text-amber-400" />
                      <span className="text-xs text-amber-400">+{s.delayMinutes} min</span>
                    </div>
                  )}
                </td>
                <td className="px-3 py-2">
                  <RiskBadge level={s.riskLevel} />
                </td>
                <td className="px-3 py-2">
                  <span className="text-slate-400 text-xs">{s.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Package({ size, className }: { size: number; className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M16.5 9.4 7.55 4.24"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" x2="12" y1="22" y2="12"/>
    </svg>
  );
}
