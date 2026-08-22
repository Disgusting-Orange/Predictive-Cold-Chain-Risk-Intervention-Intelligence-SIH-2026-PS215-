import type { RouteOption } from '../types';
import { RISK_COLORS } from '../types';
import { Route, Clock, Shield, Star } from 'lucide-react';

interface Props {
  options: RouteOption[];
}

function getRiskColor(risk: number): string {
  if (risk >= 75) return RISK_COLORS.CRITICAL;
  if (risk >= 50) return RISK_COLORS.HIGH;
  if (risk >= 30) return RISK_COLORS.MEDIUM;
  return RISK_COLORS.LOW;
}

export default function RouteOptions({ options }: Props) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Route size={14} className="text-blue-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Route Alternatives
        </span>
      </div>

      <div className="space-y-2">
        {options.map((opt) => {
          const riskColor = getRiskColor(opt.predictedRisk);
          return (
            <div
              key={opt.id}
              className="rounded-lg p-3 border flex items-center gap-3 transition-colors"
              style={{
                background: opt.isRecommended
                  ? 'rgba(34,197,94,0.06)'
                  : 'rgba(30,41,59,0.4)',
                borderColor: opt.isRecommended
                  ? 'rgba(34,197,94,0.25)'
                  : 'rgba(148,163,184,0.08)',
              }}
            >
              {opt.isRecommended && (
                <Star
                  size={16}
                  className="shrink-0"
                  fill="#22c55e"
                  color="#22c55e"
                />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-200">
                    {opt.name}
                  </span>
                  {opt.isRecommended && (
                    <span className="text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded font-medium">
                      RECOMMENDED
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {opt.description}
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <div className="text-center">
                  <div className="flex items-center gap-1 text-slate-300">
                    <Clock size={12} className="text-slate-500" />
                    <span className="font-mono text-sm font-semibold">
                      {opt.etaMinutes} min
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">ETA</div>
                </div>
                <div className="text-center">
                  <div className="flex items-center gap-1">
                    <Shield size={12} style={{ color: riskColor }} />
                    <span
                      className="font-mono text-sm font-semibold"
                      style={{ color: riskColor }}
                    >
                      {opt.predictedRisk}%
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">Risk</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
