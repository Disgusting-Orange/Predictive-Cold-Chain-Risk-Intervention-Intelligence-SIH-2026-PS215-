import { Play, Thermometer, Clock, Merge, RotateCcw } from 'lucide-react';

interface Props {
  scenario: string;
  onScenario: (s: string) => void;
}

const scenarios = [
  {
    id: 'normal',
    label: 'Normal',
    icon: Play,
    color: '#22c55e',
    bg: 'rgba(34,197,94,0.12)',
    border: 'rgba(34,197,94,0.25)',
  },
  {
    id: 'temp_failure',
    label: 'Temp Failure',
    icon: Thermometer,
    color: '#f97316',
    bg: 'rgba(249,115,22,0.12)',
    border: 'rgba(249,115,22,0.25)',
  },
  {
    id: 'traffic_delay',
    label: 'Traffic Delay',
    icon: Clock,
    color: '#eab308',
    bg: 'rgba(234,179,8,0.12)',
    border: 'rgba(234,179,8,0.25)',
  },
  {
    id: 'combined',
    label: 'Combined Failure',
    icon: Merge,
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.12)',
    border: 'rgba(239,68,68,0.25)',
    primary: true,
  },
  {
    id: 'reset',
    label: 'Reset Demo',
    icon: RotateCcw,
    color: '#3b82f6',
    bg: 'rgba(59,130,246,0.12)',
    border: 'rgba(59,130,246,0.25)',
  },
];

export default function ScenarioControls({ scenario, onScenario }: Props) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 uppercase tracking-wider mr-1">
        Scenario:
      </span>
      {scenarios.map((s) => {
        const isActive = scenario === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onScenario(s.id)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all hover:scale-[1.03] active:scale-[0.97]"
            style={{
              background: isActive ? s.bg : 'rgba(30,41,59,0.5)',
              border: `1px solid ${isActive ? s.border : 'rgba(148,163,184,0.1)'}`,
              color: isActive ? s.color : '#94a3b8',
              cursor: 'pointer',
              boxShadow: s.primary && !isActive
                ? '0 0 15px rgba(239,68,68,0.15)'
                : 'none',
            }}
          >
            <s.icon size={12} />
            {s.label}
          </button>
        );
      })}
    </div>
  );
}
