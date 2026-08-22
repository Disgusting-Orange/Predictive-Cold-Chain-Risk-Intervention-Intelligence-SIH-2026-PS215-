import type { Shipment } from '../types';
import { RISK_COLORS } from '../types';
import {
  Thermometer,
  Droplets,
  Gauge,
  Clock,
  Timer,
  DoorOpen,
  DoorClosed,
  Battery,
} from 'lucide-react';

interface Props {
  shipment: Shipment;
}

interface TelemetryCardProps {
  label: string;
  value: string;
  unit?: string;
  icon: React.ReactNode;
  color?: string;
  alert?: boolean;
}

function TelemetryCard({ label, value, unit, icon, color = '#94a3b8', alert }: TelemetryCardProps) {
  return (
    <div
      className="rounded-lg px-3 py-2.5 border"
      style={{
        background: alert ? `${RISK_COLORS.CRITICAL}10` : 'rgba(30,41,59,0.5)',
        borderColor: alert ? `${RISK_COLORS.CRITICAL}30` : 'rgba(148,163,184,0.1)',
      }}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span style={{ color }}>{icon}</span>
        <span className="text-xs text-slate-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-lg font-bold font-mono" style={{ color }}>
          {value}
        </span>
        {unit && <span className="text-xs text-slate-500">{unit}</span>}
      </div>
    </div>
  );
}

export default function TelemetryCards({ shipment }: Props) {
  const s = shipment;
  const tempColor =
    s.temperature >= s.safeMaxTemp
      ? RISK_COLORS.CRITICAL
      : s.temperature >= s.safeMaxTemp - 1
        ? RISK_COLORS.HIGH
        : s.temperature >= s.safeMaxTemp - 2
          ? RISK_COLORS.MEDIUM
          : '#22c55e';

  return (
    <div className="grid grid-cols-4 gap-2">
      <TelemetryCard
        label="Temperature"
        value={s.temperature.toFixed(1)}
        unit="°C"
        icon={<Thermometer size={14} />}
        color={tempColor}
        alert={s.temperature >= s.safeMaxTemp - 0.5}
      />
      <TelemetryCard
        label="Humidity"
        value={s.humidity.toString()}
        unit="%"
        icon={<Droplets size={14} />}
        color="#3b82f6"
      />
      <TelemetryCard
        label="Speed"
        value={s.speed.toString()}
        unit="km/h"
        icon={<Gauge size={14} />}
        color={s.speed < 10 ? RISK_COLORS.MEDIUM : '#8b5cf6'}
      />
      <TelemetryCard
        label="ETA"
        value={s.etaMinutes.toString()}
        unit="min"
        icon={<Clock size={14} />}
        color="#06b6d4"
      />
      <TelemetryCard
        label="Delay"
        value={s.delayMinutes > 0 ? `+${s.delayMinutes}` : '0'}
        unit="min"
        icon={<Timer size={14} />}
        color={s.delayMinutes > 10 ? RISK_COLORS.HIGH : s.delayMinutes > 0 ? RISK_COLORS.MEDIUM : '#22c55e'}
        alert={s.delayMinutes > 15}
      />
      <TelemetryCard
        label="Door"
        value={s.doorOpen ? 'OPEN' : 'CLOSED'}
        icon={s.doorOpen ? <DoorOpen size={14} /> : <DoorClosed size={14} />}
        color={s.doorOpen ? RISK_COLORS.CRITICAL : '#22c55e'}
        alert={s.doorOpen}
      />
      <TelemetryCard
        label="Battery"
        value={s.battery.toFixed(0)}
        unit="%"
        icon={<Battery size={14} />}
        color={s.battery < 30 ? RISK_COLORS.HIGH : '#22c55e'}
      />
      <TelemetryCard
        label="Trend"
        value={s.temperatureTrend > 0 ? `+${s.temperatureTrend.toFixed(1)}` : s.temperatureTrend.toFixed(1)}
        unit="°C/t"
        icon={<Thermometer size={14} />}
        color={s.temperatureTrend > 0.3 ? RISK_COLORS.CRITICAL : s.temperatureTrend > 0 ? RISK_COLORS.MEDIUM : '#22c55e'}
      />
    </div>
  );
}
