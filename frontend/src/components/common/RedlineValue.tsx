interface Props {
  before: string;
  after: string;
  /** 被涂改的字符区间 [start, end)；不传则整段划掉 */
  span?: number[];
}

/** 涂改对照：原文划红线 → 脱敏后值。策略预览与 PII 证据两页共用。 */
export const RedlineValue = ({ before, after, span }: Props) => {
  const hasSpan = Array.isArray(span) && span.length === 2 && span[1] > span[0];
  const start = hasSpan ? span[0] : 0;
  const end = hasSpan ? span[1] : before.length;
  const head = before.slice(0, start);
  const struck = before.slice(start, end);
  const tail = before.slice(end);
  return (
    <span className="redline-pair">
      <span className="redline-before">
        {head}
        <span style={{ textDecorationThickness: '3px' }}>{struck}</span>
        {tail}
      </span>
      <span className="redline-arrow">→</span>
      <span className="redline-after">{after}</span>
    </span>
  );
};
