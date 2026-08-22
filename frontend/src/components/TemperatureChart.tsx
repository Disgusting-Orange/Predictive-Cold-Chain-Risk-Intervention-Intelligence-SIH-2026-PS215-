import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { TemperatureReading } from '../types';
import { Activity } from 'lucide-react';

interface Props {
  history: TemperatureReading[];
  safeMin: number;
  safeMax: number;
}

export default function TemperatureChart({ history, safeMin, safeMax }: Props) {
  // Split data into observed and predicted for dual-line rendering
  const chartData = history.map((r, i) => ({
    time: r.time,
    observed: r.isPredicted ? undefined : r.temperature,
    predicted: r.isPredicted ? r.temperature : undefined,
    // Connect the line: last observed point should also be in predicted
    ...(
      !r.isPredicted &&
      i < history.length - 1 &&
      history[i + 1]?.isPredicted
        ? { predicted: r.temperature }
        : {}
    ),
  }));

  const allTemps = history.map((r) => r.temperature);
  const minTemp = Math.min(...allTemps, safeMin) - 1;
  const maxTemp = Math.max(...allTemps, safeMax) + 2;

  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Activity size={14} className="text-cyan-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Temperature Timeline
        </span>
        <span className="text-xs text-slate-600 ml-auto">
          Prototype predictive analytics
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />

          {/* Safe temperature zone */}
          <ReferenceArea
            y1={safeMin}
            y2={safeMax}
            fill="rgba(34,197,94,0.06)"
            strokeOpacity={0}
          />

          {/* Unsafe threshold line */}
          <ReferenceLine
            y={safeMax}
            stroke="#ef4444"
            strokeDasharray="6 3"
            strokeWidth={1.5}
            label={{
              value: `Unsafe: ${safeMax}°C`,
              position: 'right',
              fill: '#ef4444',
              fontSize: 10,
            }}
          />
          <ReferenceLine
            y={safeMin}
            stroke="#3b82f6"
            strokeDasharray="6 3"
            strokeWidth={1}
            label={{
              value: `Min: ${safeMin}°C`,
              position: 'right',
              fill: '#3b82f6',
              fontSize: 10,
            }}
          />

          <XAxis
            dataKey="time"
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
            tickLine={false}
          />
          <YAxis
            domain={[minTemp, maxTemp]}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
            tickLine={false}
            tickFormatter={(v: number) => `${v.toFixed(0)}°`}
          />
          <Tooltip
            contentStyle={{
              background: '#1e293b',
              border: '1px solid rgba(148,163,184,0.2)',
              borderRadius: '8px',
              fontSize: '12px',
              color: '#e2e8f0',
            }}
            formatter={(value: number, name: string) => [
              `${value.toFixed(1)}°C`,
              name === 'observed' ? 'Observed' : 'Predicted',
            ]}
          />
          <Legend
            wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }}
            formatter={(value: string) =>
              value === 'observed' ? '● Observed' : '◇ Predicted'
            }
          />

          {/* Observed temperature line */}
          <Line
            type="monotone"
            dataKey="observed"
            stroke="#06b6d4"
            strokeWidth={2.5}
            dot={{ fill: '#06b6d4', r: 3, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: '#06b6d4' }}
            connectNulls={false}
            name="observed"
          />

          {/* Predicted temperature line (visually distinct) */}
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#f59e0b"
            strokeWidth={2}
            strokeDasharray="8 4"
            dot={{ fill: '#f59e0b', r: 3, strokeWidth: 2, stroke: '#1e293b' }}
            activeDot={{ r: 5, fill: '#f59e0b' }}
            connectNulls={false}
            name="predicted"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
