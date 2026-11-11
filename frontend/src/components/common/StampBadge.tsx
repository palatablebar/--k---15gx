import type { CSSProperties, ReactNode } from 'react';

type Tone = 'stamp' | 'ok' | 'warn' | 'muted';

interface Props {
  children: ReactNode;
  tone?: Tone;
  rotate?: number;
  title?: string;
  className?: string;
}

/** 印泥印章：状态、结论、审批意见统一用它，带一次落章动效。 */
export const StampBadge = ({ children, tone = 'stamp', rotate = -4, title, className }: Props) => {
  const style: CSSProperties = { transform: `rotate(${rotate}deg)` };
  return (
    <span className={`stamp stamp-${tone} ${className ?? ''}`} style={style} title={title}>
      {children}
    </span>
  );
};
