export interface StatItem {
  label: string;
  value: string | number;
  tone?: 'ink' | 'stamp' | 'olive' | 'amber';
}

interface Props {
  items: StatItem[];
}

const toneColor = (tone: StatItem['tone']): string => {
  switch (tone) {
    case 'stamp':
      return 'var(--stamp-deep)';
    case 'olive':
      return 'var(--olive)';
    case 'amber':
      return 'var(--amber)';
    default:
      return 'var(--ink)';
  }
};

/** 横向统计条：数据集摘要、校验结论、台账统计共用。 */
export const StatStrip = ({ items }: Props) => (
  <div className="stat-strip">
    {items.map((item) => (
      <div className="stat" key={item.label}>
        <div className="stat-value num" style={{ color: toneColor(item.tone) }}>
          {item.value}
        </div>
        <div className="stat-label">{item.label}</div>
      </div>
    ))}
  </div>
);
