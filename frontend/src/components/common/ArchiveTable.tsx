import type { ReactNode } from 'react';
import { EmptyState } from './EmptyState';

export interface ArchiveColumn<T> {
  key: string;
  header: string;
  width?: string;
  align?: 'left' | 'right';
  render: (row: T) => ReactNode;
}

interface Props<T> {
  columns: ArchiveColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyHint?: string;
}

/** 档案表：细边框、无圆角、表头小字距——数据集/台账/候选层级共用。 */
export function ArchiveTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  emptyTitle = '暂无记录',
  emptyHint = '调整筛选条件，或先完成一次扫描。',
}: Props<T>) {
  if (!rows.length) return <EmptyState title={emptyTitle} hint={emptyHint} />;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                style={{ width: column.width, textAlign: column.align === 'right' ? 'right' : 'left' }}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className={onRowClick ? 'row-click' : undefined}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((column) => (
                <td key={column.key} className={column.align === 'right' ? 'right' : undefined}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
