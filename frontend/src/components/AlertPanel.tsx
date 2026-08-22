import type { Alert } from '../types';
import { RISK_COLORS } from '../types';
import {
  AlertTriangle,
  AlertOctagon,
  Info,
  Bell,
  ShieldAlert,
} from 'lucide-react';

interface Props {
  alerts: Alert[];
}

function getAlertIcon(severity: string) {
  switch (severity) {
    case 'CRITICAL':
      return <AlertOctagon size={14} />;
    case 'HIGH':
      return <ShieldAlert size={14} />;
    case 'MEDIUM':
      return <AlertTriangle size={14} />;
    case 'INFO':
      return <Info size={14} />;
    default:
      return <Bell size={14} />;
  }
}

function getAlertColor(severity: string): string {
  return RISK_COLORS[severity] || '#94a3b8';
}

export default function AlertPanel({ alerts }: Props) {
  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div
        className="px-4 py-2.5 border-b flex items-center gap-2"
        style={{ borderColor: 'rgba(148,163,184,0.1)' }}
      >
        <Bell size={14} className="text-amber-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Active Alerts
        </span>
        {alerts.length > 0 && (
          <span className="ml-auto bg-amber-500/20 text-amber-400 text-xs font-bold px-2 py-0.5 rounded-full">
            {alerts.length}
          </span>
        )}
      </div>
      <div className="overflow-auto" style={{ maxHeight: '160px' }}>
        {alerts.length === 0 ? (
          <div className="px-4 py-6 text-center text-slate-500 text-sm">
            No active alerts
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'rgba(148,163,184,0.06)' }}>
            {alerts.map((alert) => {
              const color = getAlertColor(alert.severity);
              return (
                <div
                  key={alert.id}
                  className="px-4 py-2.5 flex items-start gap-3 transition-colors"
                  style={{
                    borderBottom: '1px solid rgba(148,163,184,0.06)',
                  }}
                >
                  <div
                    className="mt-0.5 shrink-0"
                    style={{ color }}
                  >
                    {getAlertIcon(alert.severity)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-200">{alert.message}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {alert.timestamp}
                    </div>
                  </div>
                  <span
                    className="text-xs font-bold px-1.5 py-0.5 rounded shrink-0"
                    style={{
                      color,
                      background: `${color}15`,
                    }}
                  >
                    {alert.severity}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
