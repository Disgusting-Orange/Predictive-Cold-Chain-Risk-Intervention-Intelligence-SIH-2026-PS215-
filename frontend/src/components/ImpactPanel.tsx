import type { ImpactData } from '../types';
import { RISK_COLORS } from '../types';
import { TrendingDown, IndianRupee } from 'lucide-react';

interface Props {
  impact: ImpactData;
}

export default function ImpactPanel({ impact }: Props) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <TrendingDown size={14} className="text-green-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Estimated Impact
        </span>
        <span className="ml-auto text-xs text-slate-600">
          Prototype simulation estimate
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* Without Intervention */}
        <div
          className="rounded-lg p-3"
          style={{
            background: 'rgba(239,68,68,0.06)',
            border: '1px solid rgba(239,68,68,0.12)',
          }}
        >
          <div className="text-xs text-slate-500 uppercase mb-2">
            Without Intervention
          </div>
          <div className="space-y-1.5">
            <div>
              <span className="text-xs text-slate-500">Risk: </span>
              <span
                className="font-mono font-bold"
                style={{ color: RISK_COLORS.CRITICAL }}
              >
                {impact.withoutIntervention.risk}%
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500">Est. Cargo Loss: </span>
              <span
                className="font-mono font-bold"
                style={{ color: RISK_COLORS.CRITICAL }}
              >
                ₹{impact.withoutIntervention.estimatedLoss.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>

        {/* With Intervention */}
        <div
          className="rounded-lg p-3"
          style={{
            background: 'rgba(34,197,94,0.06)',
            border: '1px solid rgba(34,197,94,0.12)',
          }}
        >
          <div className="text-xs text-slate-500 uppercase mb-2">
            With Intervention
          </div>
          <div className="space-y-1.5">
            <div>
              <span className="text-xs text-slate-500">Risk: </span>
              <span
                className="font-mono font-bold"
                style={{ color: '#22c55e' }}
              >
                {impact.withIntervention.risk}%
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500">Est. Cargo Loss: </span>
              <span
                className="font-mono font-bold"
                style={{ color: '#22c55e' }}
              >
                ₹{impact.withIntervention.estimatedLoss.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Row */}
      <div
        className="rounded-lg p-3 flex items-center justify-between"
        style={{
          background: 'rgba(34,197,94,0.08)',
          border: '1px solid rgba(34,197,94,0.15)',
        }}
      >
        <div className="flex items-center gap-3">
          <IndianRupee size={18} className="text-green-400" />
          <div>
            <div className="text-xs text-slate-500 uppercase">
              Estimated Loss Avoided
            </div>
            <div className="text-xl font-bold font-mono text-green-400">
              ₹{impact.lossAvoided.toLocaleString('en-IN')}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-500 uppercase">
            Risk Reduction
          </div>
          <div className="text-xl font-bold font-mono text-green-400">
            {impact.riskReduction}%
          </div>
        </div>
      </div>
    </div>
  );
}
