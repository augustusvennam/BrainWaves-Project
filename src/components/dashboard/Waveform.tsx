import { memo, useEffect, useRef } from 'react';
import type { EegSample } from '../../types/dashboard';

interface Props { samples: EegSample[]; channel: string; seconds?: number; scale?: [number, number]; filtered?: boolean }
export const Waveform = memo(function Waveform({ samples, channel, seconds = 10, scale, filtered = false }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const current = useRef({samples, channel, seconds, scale});
  current.current = {samples, channel, seconds, scale};
  const redraw = useRef<() => void>(() => {});
  useEffect(() => redraw.current(), [samples, channel, seconds, scale]);
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    function draw() {
      if (!element) return;
      const {samples, channel, seconds, scale} = current.current;
      const width = element.clientWidth;
      const height = 160;
      const ratio = window.devicePixelRatio || 1;
      element.width = width * ratio;
      element.height = height * ratio;
      const context = element.getContext('2d');
      if (!context) return;
      context.scale(ratio, ratio);
      context.clearRect(0, 0, width, height);
      const endTime = samples.at(-1)?.time ?? 0;
      const valid = samples.filter(sample => sample.time >= endTime - seconds && Number.isFinite(sample.values[channel]));
      if (valid.length < 2) return;
      const values = valid.map(sample => sample.values[channel]);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const padding = Math.max((max - min) * 0.1, 1);
      const low = scale?.[0] ?? min - padding;
      const high = scale?.[1] ?? max + padding;
      const end = valid.at(-1)!.time;
      const start = end - seconds;
      context.font = '11px monospace';
      context.fillStyle = '#a6a9b3';
      context.strokeStyle = '#292c35';
      for (let i = 0; i < 3; i++) {
        const y = 18 + i * 58;
        context.beginPath(); context.moveTo(65, y); context.lineTo(width, y); context.stroke();
        context.fillText(`${(high - i * (high - low) / 2).toFixed(1)}`, 2, y + 4);
      }
      context.strokeStyle = '#929dff';
      context.lineWidth = 1.5;
      context.beginPath();
      let previous: EegSample | undefined;
      samples.filter(s => s.time >= start).forEach(sample => {
        if (!Number.isFinite(sample.values[channel])) {previous = undefined; return;}
        const x = 65 + ((sample.time - start) / seconds) * (width - 70);
        const y = 18 + (1 - (sample.values[channel] - low) / (high - low)) * 116;
        // Break the trace across gaps rather than imply continuous acquisition.
        if (!previous || sample.time - previous.time > 0.1) context.moveTo(x, y);
        else context.lineTo(x, y);
        previous = sample;
      });
      context.stroke();
      context.fillText(`-${seconds} s`, 65, 155);
      context.fillText('latest', Math.max(65, width - 50), 155);
    }
    redraw.current = draw;
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return <canvas ref={canvas} className="waveform" role="img" aria-label={`${channel} ${filtered ? 'filtered' : 'raw'} EEG amplitude in microvolts, last ${seconds} seconds`} />;
});
