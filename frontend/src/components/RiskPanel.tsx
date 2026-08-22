import type { ContributingFactor } from '../types';
import { RISK_COLORS } from '../types';
import { Shield } from 'lucide-react';

interface Props {
  riskScore: number;
  riskLevel: string;
  factors: ContributingFactor[];
}

export default function RiskPanel({ riskScore, riskLevel, factors }: Props) {
  const color = RISK_COLORS[riskLevel] || '#94a3b8';

  // Circular progress ring
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const progress = (riskScore / 100) * circumference;

  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Shield size={14} style={{ color }} />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Risk Assessment
        </span>
        <span className="ml-auto text-xs text-slate-600">
          Prototype risk engine
        </span>
      </div>

      <div className="flex items-start gap-4">
        {/* Risk Score Ring */}
        <div className="relative shrink-0">
          <svg width="90" height="90" viewBox="0 0 90 90">
            {/* Background ring */}
            <circle
              cx="45"
              cy="45"
              r={radius}
              fill="none"
              stroke="rgba(148,163,184,0.1)"
              strokeWidth="6"
            />
            {/* Progress ring */}
            <circle
              cx="45"
              cy="45"
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - progress}
              transform="rotate(-90 45 45)"
              style={{ transition: 'stroke-dashoffset 0.5s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-bold font-mono" style={{ color }}>
              {riskScore}
            </span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
        </div>

        {/* Risk Level + Factors */}
        <div className="flex-1">
          <div
            className="inline-block px-3 py-1 rounded-lg text-sm font-bold uppercase tracking-wide mb-3"
            style={{
              color,
              background: `${color}15`,
              border: `1px solid ${color}30`,
            }}
          >
            {riskLevel}
          </div>

          <div className="space-y-1.5">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Contributing Factors
            </div>
            {factors.map((f, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span
                  className="shrink-0 font-mono text-xs mt-0.5"
                  style={{
                    color:
                      f.direction === '↑'
                        ? RISK_COLORS.CRITICAL
                        : f.direction === '↓'
                          ? '#22c55e'
                          : '#64748b',
                  }}
                >
                  {f.direction}
                </span>
                <span className="text-slate-300">{f.description}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
