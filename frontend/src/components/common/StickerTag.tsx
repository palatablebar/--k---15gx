import type { ReactNode } from 'react';

interface Props {
  label: string;
  children?: ReactNode;
  rotate?: number;
  tone?: 'plain' | 'red' | 'olive';
}

/** 标签贴纸：表格里的方法/角色/敏感级别标记。 */
export const StickerTag = ({ label, children, rotate = -1.6, tone = 'plain' }: Props) => {
  const color =
    tone === 'red' ? 'var(--stamp-deep)' : tone === 'olive' ? 'var(--olive)' : 'var(--ink-soft)';
  return (
    <span className="sticker" style={{ transform: `rotate(${rotate}deg)`, color }} title={label}>
      {label}
      {children ? <span style={{ marginLeft: 6, color: 'var(--ink)' }}>{children}</span> : null}
    </span>
  );
};
