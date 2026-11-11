import type { SensitivityLevel } from '../../types/models';
import { SENSITIVITY_LABELS } from '../../constants/enums';
import { sensitivityScore, sensitivityVar } from '../../utils/heat';

interface Props {
  level: SensitivityLevel | string;
  showLabel?: boolean;
}

/** 敏感度热力条：低→极高 长度与颜色同步升温。 */
export const SensitivityBar = ({ level, showLabel = true }: Props) => (
  <span className="row" style={{ gap: 7 }}>
    <span className="heat-bar" title={`敏感度：${SENSITIVITY_LABELS[level as SensitivityLevel] ?? level}`}>
      <span style={{ width: `${sensitivityScore(level) * 100}%`, background: sensitivityVar(level) }} />
    </span>
    {showLabel ? (
      <span style={{ fontSize: 11, color: sensitivityVar(level) }}>
        {SENSITIVITY_LABELS[level as SensitivityLevel] ?? level}
      </span>
    ) : null}
  </span>
);
