import type { Warehouse } from '../types';
import {
  Warehouse as WarehouseIcon,
  Thermometer,
  Droplets,
  Server,
  Zap,
  Package,
  Calendar,
  Activity,
} from 'lucide-react';

interface Props {
  warehouses: Warehouse[];
}

function CoolingStatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; bg: string; label: string }> = {
    operational: { color: '#22c55e', bg: 'rgba(34,197,94,0.15)', label: 'Operational' },
    degraded: { color: '#f97316', bg: 'rgba(249,115,22,0.15)', label: 'Degraded' },
    offline: { color: '#ef4444', bg: 'rgba(239,68,68,0.15)', label: 'Offline' },
  };
  const c = config[status] || config.operational;
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide inline-flex items-center gap-1"
      style={{ color: c.color, background: c.bg, border: `1px solid ${c.color}30` }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full inline-block"
        style={{
          background: c.color,
          boxShadow: status === 'operational' ? `0 0 6px ${c.color}` : 'none',
          animation: status === 'operational' ? 'pulse-dot 2s ease-in-out infinite' : 'none',
        }}
      />
      {c.label}
    </span>
  );
}

function PowerBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string }> = {
    grid: { color: '#22c55e', label: 'Grid' },
    backup: { color: '#eab308', label: 'Backup' },
    degraded: { color: '#ef4444', label: 'Degraded' },
  };
  const c = config[status] || config.grid;
  return (
    <span className="flex items-center gap-1 text-xs" style={{ color: c.color }}>
      <Zap size={10} />
      {c.label}
    </span>
  );
}

function CapacityBar({ capacity }: { capacity: number }) {
  const color =
    capacity >= 90 ? '#ef4444' : capacity >= 70 ? '#f97316' : capacity >= 50 ? '#eab308' : '#22c55e';
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500">Capacity</span>
        <span className="text-xs font-mono font-bold" style={{ color }}>
          {capacity}%
        </span>
      </div>
      <div
        className="w-full h-1.5 rounded-full overflow-hidden"
        style={{ background: 'rgba(148,163,184,0.1)' }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${capacity}%`,
            background: `linear-gradient(90deg, ${color}80, ${color})`,
            boxShadow: capacity >= 90 ? `0 0 8px ${color}50` : 'none',
          }}
        />
      </div>
    </div>
  );
}

export default function WarehousePanel({ warehouses }: Props) {
  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <style>
        {`
          @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
        `}
      </style>
      <div
        className="px-4 py-2.5 border-b flex items-center gap-2"
        style={{ borderColor: 'rgba(148,163,184,0.1)' }}
      >
        <WarehouseIcon size={14} className="text-purple-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Warehouse Facilities
        </span>
        <span className="ml-auto bg-purple-500/20 text-purple-400 text-xs font-bold px-2 py-0.5 rounded-full">
          {warehouses.length}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 p-2">
        {warehouses.map((wh) => (
          <div
            key={wh.warehouseId}
            className="rounded-lg border p-3 transition-all hover:border-purple-500/30"
            style={{
              background: 'rgba(30,41,59,0.4)',
              borderColor: 'rgba(148,163,184,0.08)',
            }}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="text-sm font-semibold text-slate-200 leading-tight">
                  {wh.name}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className="text-xs px-1.5 py-0.5 rounded font-medium uppercase"
                    style={{
                      background:
                        wh.type === 'distribution'
                          ? 'rgba(59,130,246,0.15)'
                          : 'rgba(6,182,212,0.15)',
                      color: wh.type === 'distribution' ? '#3b82f6' : '#06b6d4',
                    }}
                  >
                    {wh.type === 'distribution' ? 'Distribution' : 'Cold Storage'}
                  </span>
                  <PowerBadge status={wh.powerStatus} />
                </div>
              </div>
              <CoolingStatusBadge status={wh.coolingStatus} />
            </div>

            {/* Telemetry Grid */}
            <div className="grid grid-cols-3 gap-1.5 mb-2">
              <div className="rounded px-2 py-1" style={{ background: 'rgba(15,23,42,0.5)' }}>
                <div className="flex items-center gap-1 text-slate-500">
                  <Thermometer size={10} />
                  <span className="text-xs">Temp</span>
                </div>
                <div className="text-sm font-mono font-bold text-slate-200">
                  {wh.temperature.toFixed(1)}°C
                </div>
              </div>
              <div className="rounded px-2 py-1" style={{ background: 'rgba(15,23,42,0.5)' }}>
                <div className="flex items-center gap-1 text-slate-500">
                  <Droplets size={10} />
                  <span className="text-xs">Humid</span>
                </div>
                <div className="text-sm font-mono font-bold text-slate-200">
                  {wh.humidity}%
                </div>
              </div>
              <div className="rounded px-2 py-1" style={{ background: 'rgba(15,23,42,0.5)' }}>
                <div className="flex items-center gap-1 text-slate-500">
                  <Package size={10} />
                  <span className="text-xs">Items</span>
                </div>
                <div className="text-sm font-mono font-bold text-slate-200">
                  {wh.inventoryCount}
                </div>
              </div>
            </div>

            {/* Capacity Bar */}
            <CapacityBar capacity={wh.capacity} />

            {/* Footer */}
            <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
              <div className="flex items-center gap-1">
                <Server size={10} />
                <span>
                  {wh.activeBays}/{wh.totalBays} bays
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Activity size={10} />
                <span>
                  Set: {wh.tempSetpoint}°C
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Calendar size={10} />
                <span>{wh.lastInspection}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
