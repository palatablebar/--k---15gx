import type { SensitivityLevel } from '../types/models';

/** 敏感度热力：低→中→高→极高 逐级升温，颜色全部来自 tokens.css 的 oklch 变量。 */
export const sensitivityVar = (level: SensitivityLevel | string): string => {
  switch (level) {
    case 'critical':
      return 'var(--stamp)';
    case 'high':
      return 'var(--amber)';
    case 'medium':
      return 'var(--olive)';
    default:
      return 'var(--ink-faint)';
  }
};

export const sensitivityScore = (level: SensitivityLevel | string): number => {
  switch (level) {
    case 'critical':
      return 1;
    case 'high':
      return 0.72;
    case 'medium':
      return 0.42;
    default:
      return 0.16;
  }
};
