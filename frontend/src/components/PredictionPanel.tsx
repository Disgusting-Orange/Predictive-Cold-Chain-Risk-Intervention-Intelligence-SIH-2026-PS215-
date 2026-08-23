import type { Prediction } from '../types';
import { RISK_COLORS } from '../types';
import { TrendingUp, Clock, AlertTriangle } from 'lucide-react';

interface Props {
  prediction: Prediction;
}

export default function PredictionPanel({ prediction }: Props) {
  const riskColor =
    prediction.excursionRisk >= 75
      ? RISK_COLORS.CRITICAL
      : prediction.excursionRisk >= 50
        ? RISK_COLORS.HIGH
        : prediction.excursionRisk >= 30
          ? RISK_COLORS.MEDIUM
          : RISK_COLORS.LOW;

  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp size={14} className="text-amber-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Edge ML Risk Forecast (60 min)
        </span>
        <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
          SHAP Explained
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        {/* Excursion Risk */}
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: `${riskColor}10` }}
        >
          <div className="text-xs text-slate-500 uppercase mb-1">
            Excursion Risk
          </div>
          <div className="text-2xl font-bold font-mono" style={{ color: riskColor }}>
            {prediction.excursionRisk}%
          </div>
        </div>

        {/* Time to Unsafe */}
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'rgba(30,41,59,0.5)' }}
        >
          <div className="text-xs text-slate-500 uppercase mb-1">
            Time to Unsafe
          </div>
          <div className="text-2xl font-bold font-mono text-slate-200 flex items-center justify-center gap-1">
            <Clock size={16} className="text-slate-400" />
            {prediction.timeToUnsafe !== null
              ? `${prediction.timeToUnsafe} min`
              : '—'}
          </div>
        </div>

        {/* Temperature Trend */}
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'rgba(30,41,59,0.5)' }}
        >
          <div className="text-xs text-slate-500 uppercase mb-1">
            Temp Trend
          </div>
          <div
            className="text-2xl font-bold font-mono"
            style={{
              color:
                prediction.temperatureTrend > 0.3
                  ? RISK_COLORS.CRITICAL
                  : prediction.temperatureTrend > 0
                    ? RISK_COLORS.MEDIUM
                    : '#22c55e',
            }}
          >
            {prediction.temperatureTrend > 0 ? '+' : ''}
            {prediction.temperatureTrend.toFixed(1)}°C
          </div>
          <div className="text-xs text-slate-500">per interval</div>
        </div>
      </div>

      {/* Prediction message */}
      {prediction.message && (
        <div
          className="rounded-lg px-3 py-2 flex items-center gap-2 text-sm"
          style={{
            background:
              prediction.excursionRisk >= 50
                ? `${RISK_COLORS.HIGH}10`
                : 'rgba(30,41,59,0.5)',
            border:
              prediction.excursionRisk >= 50
                ? `1px solid ${RISK_COLORS.HIGH}25`
                : '1px solid rgba(148,163,184,0.08)',
          }}
        >
          {prediction.excursionRisk >= 50 && (
            <AlertTriangle size={14} style={{ color: riskColor }} />
          )}
          <span
            style={{
              color:
                prediction.excursionRisk >= 50 ? riskColor : '#94a3b8',
            }}
          >
            {prediction.message}
          </span>
        </div>
      )}
    </div>
  );
}
