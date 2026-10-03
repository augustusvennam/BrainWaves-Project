/**
 * EEGGraph — Real-time EEG metric visualization component.
 *
 * Renders a live line chart of one Cortex performance metric (eng, exc, str, rel, int, lex)
 * using Recharts. Data is streamed via WebSocket from the Python backend.
 *
 * Props:
 *   metric   - Metric key to display (e.g. 'eng', 'exc')
 *   title    - Display title
 *   color    - Line color (hex)
 *   maxPoints- Max data points to keep in the rolling window
 *   height   - Chart height in px
 */

import { useEffect, useRef, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts';
import { Card, CardHeader, CardBody } from './Card';
import { SectionTitle } from './SectionTitle';

interface DataPoint {
  time: string;
  value: number;
}

interface EEGGraphProps {
  metric: string;
  title: string;
  color: string;
  maxPoints?: number;
  height?: number;
  threshold?: number;
}

const DEFAULT_MAX_POINTS = 20;
const DEFAULT_HEIGHT = 160;

export function EEGGraph({
  metric,
  title,
  color,
  maxPoints = DEFAULT_MAX_POINTS,
  height = DEFAULT_HEIGHT,
  threshold,
}: EEGGraphProps) {
  const [data, setData] = useState<DataPoint[]>([]);
  const [currentValue, setCurrentValue] = useState<number | null>(null);
  const subscriptionRef = useRef<((value: number) => void) | null>(null);

  // Subscribe to WebSocket updates for this metric
  useEffect(() => {
    let isMounted = true;

    const handleMetric = (value: number) => {
      if (!isMounted) return;
      const now = new Date();
      const timeLabel = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });

      setCurrentValue(value);
      setData((prev) => {
        const updated = [...prev, { time: timeLabel, value }];
        return updated.slice(-maxPoints);
      });
    };

    subscriptionRef.current = handleMetric;
    // In a real app, you'd wire this to the WebSocket service:
    // websocketService.onMessage((msg) => {
    //   if (msg.type === 'met' && msg.data[metric] !== undefined) {
    //     handleMetric(msg.data[metric]);
    //   }
    // });

    return () => {
      isMounted = false;
      subscriptionRef.current = null;
    };
  }, [metric, maxPoints]);

  const formatTooltipValue = (value: number) => [`${value.toFixed(2)}`, title];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <SectionTitle className="mb-0">{title}</SectionTitle>
          <span
            className="text-xs font-mono px-2 py-1 rounded"
            style={{
              background: `${color}22`,
              color: color,
              border: `1px solid ${color}44`,
            }}
          >
            {currentValue !== null ? currentValue.toFixed(2) : '--'}
          </span>
        </div>
      </CardHeader>
      <CardBody>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart
            data={data}
            margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-hairline)" />
            <XAxis
              dataKey="time"
              tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={formatTooltipValue}
              contentStyle={{
                background: 'var(--surface-1)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-ink)',
              }}
            />
            {threshold !== undefined && (
              <ReferenceDot
                y={threshold}
                stroke={color}
                fill={color}
                label={{
                  value: `threshold: ${threshold}`,
                  fill: 'var(--text-tertiary)',
                  fontSize: 10,
                  position: 'top',
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardBody>
    </Card>
  );
}

// Pre-configured metric graphs for the EEG dashboard
export const EEG_METRICS = [
  {
    metric: 'eng',
    title: 'Engagement',
    color: '#5e6ad2',
    threshold: 0.6,
  },
  {
    metric: 'exc',
    title: 'Excitement',
    color: '#ec4899',
    threshold: 0.5,
  },
  {
    metric: 'str',
    title: 'Stress',
    color: '#f97316',
    threshold: 0.7,
  },
  {
    metric: 'rel',
    title: 'Relaxation',
    color: '#10b981',
    threshold: 0.5,
  },
  {
    metric: 'int',
    title: 'Interest',
    color: '#8b5cf6',
    threshold: 0.5,
  },
  {
    metric: 'lex',
    title: 'Long-term Excitement',
    color: '#06b6d4',
    threshold: 0.5,
  },
] as const;