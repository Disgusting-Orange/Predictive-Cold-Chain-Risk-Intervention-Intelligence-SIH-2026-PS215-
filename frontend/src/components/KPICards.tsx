import type { KPIs } from '../types';
import { RISK_COLORS } from '../types';
import { Package, AlertTriangle, ShieldAlert, IndianRupee, Warehouse, Brain } from 'lucide-react';

interface Props {
  kpis: KPIs;
  aiRecommendationCount: number;
}

export default function KPICards({ kpis, aiRecommendationCount }: Props) {
  const cards = [
    {
      label: 'Active Shipments',
      value: kpis.activeShipments,
      icon: Package,
      color: '#3b82f6',
      bg: 'rgba(59,130,246,0.12)',
    },
    {
      label: 'At-Risk Shipments',
      value: kpis.atRiskShipments,
      icon: AlertTriangle,
      color: RISK_COLORS.HIGH,
      bg: 'rgba(249,115,22,0.12)',
    },
    {
      label: 'Critical Shipments',
      value: kpis.criticalShipments,
      icon: ShieldAlert,
      color: RISK_COLORS.CRITICAL,
      bg: 'rgba(239,68,68,0.12)',
    },
    {
      label: 'Active Warehouses',
      value: kpis.activeWarehouses,
      icon: Warehouse,
      color: '#8b5cf6',
      bg: 'rgba(139,92,246,0.12)',
    },
    {
      label: 'AI Recommendations',
      value: aiRecommendationCount,
      icon: Brain,
      color: '#a855f7',
      bg: 'rgba(168,85,247,0.12)',
    },
    {
      label: 'Est. Loss Avoided',
      value: kpis.estimatedLossAvoided > 0
        ? `₹${(kpis.estimatedLossAvoided / 1000).toFixed(0)}K`
        : '₹0',
      icon: IndianRupee,
      color: '#22c55e',
      bg: 'rgba(34,197,94,0.12)',
    },
  ];

  return (
    <div className="grid grid-cols-6 gap-2">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl px-3 py-2.5 border flex items-center gap-2"
          style={{
            background: 'rgba(15,23,42,0.6)',
            borderColor: 'rgba(148,163,184,0.12)',
          }}
        >
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: card.bg }}
          >
            <card.icon size={18} color={card.color} />
          </div>
          <div>
            <div
              className="text-xl font-bold font-mono"
              style={{ color: card.color }}
            >
              {card.value}
            </div>
            <div className="text-xs text-slate-400 uppercase tracking-wider leading-tight">
              {card.label}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
