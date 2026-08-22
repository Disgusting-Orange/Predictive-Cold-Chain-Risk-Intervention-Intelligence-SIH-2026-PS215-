import type { InterventionRecommendation } from '../types';
import { RISK_COLORS } from '../types';
import { Zap, ArrowRight, CheckCircle, Shield } from 'lucide-react';

interface Props {
  intervention: InterventionRecommendation;
  interventionApplied: boolean;
  onApply: () => void;
}

export default function InterventionPanel({
  intervention,
  interventionApplied,
  onApply,
}: Props) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: interventionApplied
          ? 'rgba(34,197,94,0.05)'
          : 'rgba(239,68,68,0.04)',
        borderColor: interventionApplied
          ? 'rgba(34,197,94,0.2)'
          : 'rgba(239,68,68,0.2)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Zap
          size={14}
          className={interventionApplied ? 'text-green-400' : 'text-amber-400'}
        />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          AI Recommended Action
        </span>
      </div>

      {/* Action Header */}
      <div
        className="rounded-lg px-4 py-3 mb-3 flex items-center gap-3"
        style={{
          background: interventionApplied
            ? 'rgba(34,197,94,0.1)'
            : 'rgba(249,115,22,0.1)',
          border: interventionApplied
            ? '1px solid rgba(34,197,94,0.2)'
            : '1px solid rgba(249,115,22,0.2)',
        }}
      >
        {interventionApplied ? (
          <CheckCircle size={20} className="text-green-400 shrink-0" />
        ) : (
          <Shield size={20} className="text-amber-400 shrink-0" />
        )}
        <div>
          <div className="text-base font-bold text-slate-100">
            {intervention.action}
          </div>
          <div className="text-xs text-slate-400">
            {interventionApplied
              ? 'Intervention active — monitoring recovery'
              : `Destination: ${intervention.destination}`}
          </div>
        </div>
      </div>

      {/* Reasons */}
      {!interventionApplied && (
        <div className="mb-4">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">
            Why?
          </div>
          <div className="space-y-1.5">
            {intervention.reasons.map((reason, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-sm text-slate-300"
              >
                <span className="text-slate-500 shrink-0">•</span>
                {reason}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Before / After comparison */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div
          className="rounded-lg p-3 text-center"
          style={{
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.15)',
          }}
        >
          <div className="text-xs text-slate-500 uppercase mb-1">
            {interventionApplied ? 'Before Intervention' : 'Current Risk'}
          </div>
          <div
            className="text-xl font-bold font-mono"
            style={{ color: RISK_COLORS.CRITICAL }}
          >
            {intervention.beforeRisk}%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            ETA: {intervention.beforeEta} min
          </div>
        </div>

        <div
          className="rounded-lg p-3 text-center"
          style={{
            background: 'rgba(34,197,94,0.08)',
            border: '1px solid rgba(34,197,94,0.15)',
          }}
        >
          <div className="text-xs text-slate-500 uppercase mb-1">
            {interventionApplied ? 'After Intervention' : 'With Intervention'}
          </div>
          <div
            className="text-xl font-bold font-mono"
            style={{ color: '#22c55e' }}
          >
            {intervention.afterRisk}%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            ETA: {intervention.afterEta} min
          </div>
        </div>
      </div>

      {/* Arrow between cards */}
      <div className="flex justify-center -mt-7 mb-3 relative z-10">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center"
          style={{
            background: '#1e293b',
            border: '2px solid rgba(148,163,184,0.2)',
          }}
        >
          <ArrowRight size={14} className="text-slate-400" />
        </div>
      </div>

      {/* Apply Button */}
      {!interventionApplied && (
        <button
          onClick={onApply}
          className="w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider transition-all hover:scale-[1.01] active:scale-[0.99]"
          style={{
            background: 'linear-gradient(135deg, #f97316, #ef4444)',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 4px 15px rgba(249,115,22,0.3)',
          }}
        >
          ⚡ Apply Intervention
        </button>
      )}
    </div>
  );
}
