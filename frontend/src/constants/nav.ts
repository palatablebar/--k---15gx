export interface NavItem {
  path: string;
  label: string;
  index: string;
  hint: string;
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/datasets', label: '数据集与列画像', index: '01', hint: '三张上游表 + 敏感度热力' },
  { path: '/pii-evidence', label: 'PII 证据', index: '02', hint: '命中明细与校验位结果' },
  { path: '/policies', label: '掩码策略预览', index: '03', hint: '应用前后样例对比' },
  { path: '/k-anonymity', label: 'k-匿名校验', index: '04', hint: '等价类与泛化建议' },
  { path: '/exports', label: '导出台账', index: '05', hint: '申请 / 审批 / 摘要' },
];
