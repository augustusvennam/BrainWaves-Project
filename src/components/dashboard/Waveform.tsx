import { useEffect, useRef } from 'react';
import type { EegSample } from '../../types/dashboard';

interface Props { samples: EegSample[]; channel: string }
export function Waveform({ samples, channel }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    function draw() {
      if (!element) return;
      const width = element.clientWidth;
      const height = 160;
      const ratio = window.devicePixelRatio || 1;
      element.width = width * ratio;
      element.height = height * ratio;
      const context = element.getContext('2d');
      if (!context) return;
      context.scale(ratio, ratio);
      context.clearRect(0, 0, width, height);
      const valid = samples.filter(sample => Number.isFinite(sample.values[channel]));
      if (valid.length < 2) return;
      const values = valid.map(sample => sample.values[channel]);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const padding = Math.max((max - min) * 0.1, 1);
      const low = min - padding;
      const high = max + padding;
      const end = valid.at(-1)!.time;
      const start = end - 10;
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
      valid.forEach((sample, index) => {
        const x = 65 + ((sample.time - start) / 10) * (width - 70);
        const y = 18 + (1 - (sample.values[channel] - low) / (high - low)) * 116;
        // Break the trace across gaps rather than imply continuous acquisition.
        if (index === 0 || sample.time - valid[index - 1].time > 0.1) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.stroke();
      context.fillText('-10 s', 65, 155);
      context.fillText('latest', Math.max(65, width - 50), 155);
    }
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(element);
    return () => observer.disconnect();
  }, [samples, channel]);
  return <canvas ref={canvas} className="waveform" role="img" aria-label={`${channel} raw EEG amplitude in microvolts, last ten seconds`} />;
}
