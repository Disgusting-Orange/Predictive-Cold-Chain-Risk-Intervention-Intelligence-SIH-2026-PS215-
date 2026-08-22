import type { AIRecommendation, ControlOverride, WarehouseControlOverride } from '../types';
import { PRIORITY_COLORS, PRIORITY_BG_COLORS } from '../types';
import {
  Brain,
  Snowflake,
  Route,
  DoorClosed,
  AlertTriangle,
  Gauge,
  Zap,
  Server,
  Package,
  ChevronRight,
  Truck,
  Warehouse,
} from 'lucide-react';

interface Props {
  recommendations: AIRecommendation[];
  onSendControl: (shipmentId: string, overrides: ControlOverride) => void;
  onSendWarehouseControl: (warehouseId: string, overrides: WarehouseControlOverride) => void;
  onApplyIntervention: (shipmentId: string) => void;
}

function getRecIcon(type: string) {
  switch (type) {
    case 'increase_cooling':
      return <Snowflake size={14} />;
    case 'reroute':
    case 'divert_delay':
      return <Route size={14} />;
    case 'close_door':
      return <DoorClosed size={14} />;
    case 'inspect':
      return <Gauge size={14} />;
    case 'pre_cool':
      return <Snowflake size={14} />;
    case 'capacity_warning':
      return <Package size={14} />;
    case 'backup_power':
      return <Zap size={14} />;
    case 'cooling_alert':
      return <Server size={14} />;
    default:
      return <AlertTriangle size={14} />;
  }
}

function getTargetIcon(targetType: string) {
  return targetType === 'warehouse' ? (
    <Warehouse size={10} />
  ) : (
    <Truck size={10} />
  );
}

export default function AIRecommendations({
  recommendations,
  onSendControl,
  onSendWarehouseControl,
  onApplyIntervention,
}: Props) {
  const handleAction = (rec: AIRecommendation) => {
    if (!rec.action) return;

    if (rec.action.type === 'control') {
      onSendControl(rec.action.targetId, rec.action.params as ControlOverride);
    } else if (rec.action.type === 'warehouse_control') {
      onSendWarehouseControl(rec.action.targetId, rec.action.params as WarehouseControlOverride);
    } else if (rec.action.type === 'intervene') {
      onApplyIntervention(rec.action.targetId);
    }
  };

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
        <Brain size={14} className="text-violet-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          AI Recommendations
        </span>
        {recommendations.length > 0 && (
          <span className="ml-auto bg-violet-500/20 text-violet-400 text-xs font-bold px-2 py-0.5 rounded-full">
            {recommendations.length}
          </span>
        )}
      </div>

      <div className="overflow-auto" style={{ maxHeight: '340px' }}>
        {recommendations.length === 0 ? (
          <div className="px-4 py-6 text-center text-slate-500 text-sm">
            <Brain size={24} className="mx-auto mb-2 text-slate-700" />
            All systems nominal — no recommendations
          </div>
        ) : (
          <div className="p-2 space-y-1.5">
            {recommendations.map((rec) => {
              const color = PRIORITY_COLORS[rec.priority] || '#3b82f6';
              const bgColor = PRIORITY_BG_COLORS[rec.priority] || 'rgba(59,130,246,0.12)';

              return (
                <div
                  key={rec.id}
                  className="rounded-lg border p-3 transition-all"
                  style={{
                    background: bgColor,
                    borderColor: `${color}25`,
                    animation:
                      rec.priority === 'URGENT'
                        ? 'rec-pulse 3s ease-in-out infinite'
                        : 'none',
                  }}
                >
                  {/* Header */}
                  <div className="flex items-start gap-2 mb-1.5">
                    <div
                      className="mt-0.5 shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
                      style={{
                        background: `${color}20`,
                        color,
                      }}
                    >
                      {getRecIcon(rec.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-200 leading-tight">
                          {rec.title}
                        </span>
                        <span
                          className="text-xs font-bold px-1.5 py-0.5 rounded shrink-0"
                          style={{
                            color,
                            background: `${color}20`,
                          }}
                        >
                          {rec.priority}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 mt-0.5 text-xs text-slate-500">
                        {getTargetIcon(rec.targetType)}
                        <span>{rec.targetName}</span>
                        <span className="mx-1">•</span>
                        <span>{rec.timestamp}</span>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <div className="text-xs text-slate-400 leading-relaxed ml-8 mb-2">
                    {rec.description}
                  </div>

                  {/* Action Button */}
                  {rec.action && (
                    <div className="ml-8">
                      <button
                        onClick={() => handleAction(rec)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider transition-all hover:scale-[1.02] active:scale-[0.98]"
                        style={{
                          background: `${color}20`,
                          color,
                          border: `1px solid ${color}30`,
                          cursor: 'pointer',
                        }}
                      >
                        <Zap size={10} />
                        Apply
                        <ChevronRight size={10} />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <style>
        {`
          @keyframes rec-pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
            50% { box-shadow: 0 0 12px 2px rgba(239,68,68,0.15); }
          }
        `}
      </style>
    </div>
  );
}
