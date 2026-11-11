interface Props {
  title: string;
  hint: string;
  action?: React.ReactNode;
}

/** 空状态教学：告诉用户下一步该做什么，而不是只写"无数据"。 */
export const EmptyState = ({ title, hint, action }: Props) => (
  <div className="empty-state">
    <div className="empty-title">{title}</div>
    <div style={{ fontSize: 12.5, maxWidth: '46ch', margin: '0 auto' }}>{hint}</div>
    {action ? <div style={{ marginTop: 14 }}>{action}</div> : null}
  </div>
);
