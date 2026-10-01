import { ArrowRight, Brain, Server, Bot } from 'lucide-react';

type Node = {
  id: string;
  label: string;
  sub: string;
  icon: React.ReactNode;
};

export function ArchitectureDiagram() {
  const nodes: Node[] = [
    {
      id: 'epoc',
      label: 'EMOTIV EPOC X',
      sub: 'EEG Headset',
      icon: <Brain className="h-5 w-5" />,
    },
    {
      id: 'cortex',
      label: 'Cortex API',
      sub: 'wss://localhost:6868',
      icon: <Server className="h-5 w-5" />,
    },
    {
      id: 'python',
      label: 'Python Controller',
      sub: 'brainbot_main.py',
      icon: <Brain className="h-5 w-5" />,
    },
    {
      id: 'temi',
      label: 'Temi Robot',
      sub: 'Mobile Platform',
      icon: <Bot className="h-5 w-5" />,
    },
  ];

  return (
    <section className="pb-8">
      <SectionTitle>Architecture</SectionTitle>
      <SectionSubtitle>Data flow: EEG capture → real-time streaming → brainwave processing → robot control</SectionSubtitle>

      <div className="relative flex flex-col items-center justify-center gap-2 md:flex-row md:items-center md:gap-2 md:w-full">
        {nodes.map((node, i) => (
          <div key={node.id} className="flex flex-col items-center gap-1.5 text-center">
            <div
              className={[
                'relative flex h-12 w-12 items-center justify-center rounded-[var(--radius-md)] bg-[var(--surface-2)] text-[var(--accent)]',
                'border border-[var(--border-hairline)]',
              ].join(' ')}
            >
              {node.icon}
            </div>
            <div className="text-xs text-[var(--text-tertiary)] line-clamp-1 max-w-[140px]">
              {node.label}
            </div>
            <div className="text-[10px] text-[var(--text-subtle)] line-clamp-1 max-w-[140px]">
              {node.sub}
            </div>
          </div>
          {i < nodes.length - 1 && (
            <ArrowRight
              className="h-5 w-5 text-[var(--accent)]"
              style={{ transform: 'rotate(90deg)' }}
            />
          )}
        ))}
      </div>
    </section>
  );
}