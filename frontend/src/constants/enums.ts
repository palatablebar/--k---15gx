/**
 * 领域枚举的前端镜像（后端 src/constants/enums.py 是唯一真相）。
 * 改枚举必须同步改两处：后端 labels 与这里。
 */
import type {
  ColumnRole,
  ExportStatus,
  MaskMethod,
  PiiType,
  SensitivityLevel,
} from '../types/models';

export const PII_TYPE_LABELS: Record<PiiType, string> = {
  mobile: '手机号',
  id_card: '身份证号',
  email: '邮箱',
  name: '姓名',
  address: '地址',
};

export const MASK_METHOD_LABELS: Record<MaskMethod, string> = {
  mask: '掩码',
  hash: '哈希',
  generalize: '泛化',
  suppress: '抑制',
};

export const MASK_METHOD_SERIES: Record<MaskMethod, string> = {
  mask: 'M',
  hash: 'H',
  generalize: 'G',
  suppress: 'S',
};

export const SENSITIVITY_LABELS: Record<SensitivityLevel, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '极高',
};

export const COLUMN_ROLE_LABELS: Record<ColumnRole, string> = {
  direct_id: '直接标识',
  quasi_id: '准标识',
  sensitive: '敏感属性',
  non_sensitive: '非敏感',
};

export const EXPORT_STATUS_LABELS: Record<ExportStatus, string> = {
  pending: '待审批',
  approved: '已批准',
  rejected: '已驳回',
};

export const BUILD_STATUS_LABELS: Record<string, string> = {
  idle: '未生成',
  queued: '排队中',
  running: '生成中',
  done: '已生成',
  failed: '生成失败',
};

export const CHECK_STATUS_LABELS: Record<string, string> = {
  queued: '排队中',
  running: '计算中',
  succeeded: '已完成',
  failed: '失败',
};

export const ACTOR_ROLE_LABELS: Record<string, string> = {
  admin: '数据平台管理员',
  dpo: '数据保护官',
  client: '科研客户',
};
