import { formatPercent } from '../../utils/format';

interface Props {
  label: string;
  value: number;
  caption?: string;
  threshold?: number;
}

/** 列级置信度：命中率 × 校验通过率 × (1 - 唯一性惩罚)。 */
export const ConfidenceMeter = ({ label, value, caption, threshold = 0.5 }: Props) => {
  const width = Math.max(0, Math.min(1, value)) * 100;
  const low = value < threshold;
  return (
    <div className="meter">
      <span className="kicker">{label}</span>
      <span className="meter-value" style={{ color: low ? 'var(--amber)' : 'var(--stamp-deep)' }}>
        {value.toFixed(4)}
      </span>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${width}%`, background: low ? 'var(--amber)' : undefined }} />
      </div>
      {caption ? (
        <span className="faint" style={{ fontSize: 10.5, gridColumn: '1 / -1' }}>
          {caption}
        </span>
      ) : null}
    </div>
  );
};
