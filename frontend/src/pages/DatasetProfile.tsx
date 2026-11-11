import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDatasetStore } from '../stores/datasetStore';
import { SectionHead } from '../components/common/SectionHead';
import { StatStrip } from '../components/common/StatStrip';
import { SensitivityBar } from '../components/common/SensitivityBar';
import { StickerTag } from '../components/common/StickerTag';
import { ArchiveTable, type ArchiveColumn } from '../components/common/ArchiveTable';
import { EmptyState } from '../components/common/EmptyState';
import { StampBadge } from '../components/common/StampBadge';
import { RoleGate } from '../components/common/RoleGate';
import { PII_TYPE_LABELS, COLUMN_ROLE_LABELS, SENSITIVITY_LABELS } from '../constants/enums';
import { formatNumber, formatPercent } from '../utils/format';
import type { DatasetColumn, DatasetTable } from '../types/models';

const tableColumns: ArchiveColumn<DatasetColumn>[] = [
  {
    key: 'ordinal',
    header: '#',
    width: '38px',
    render: (row) => <span className="mono faint">{String(row.ordinal + 1).padStart(2, '0')}</span>,
  },
  {
    key: 'name',
    header: '列名',
    render: (row) => (
      <span className="mono" style={{ fontWeight: 600 }}>
        {row.name}
      </span>
    ),
  },
  { key: 'type', header: '类型', render: (row) => <span className="faint">{row.data_type}</span> },
  {
    key: 'role',
    header: '角色',
    render: (row) => (
      <StickerTag label={COLUMN_ROLE_LABELS[row.column_role]} rotate={row.ordinal % 2 ? 1.2 : -1.6} />
    ),
  },
  { key: 'sensitivity', header: '敏感度', render: (row) => <SensitivityBar level={row.sensitivity_level} /> },
  {
    key: 'pii',
    header: 'PII 类型',
    render: (row) =>
      row.pii_type ? (
        <span style={{ color: 'var(--stamp-deep)', fontWeight: 600 }}>
          {PII_TYPE_LABELS[row.pii_type]}
        </span>
      ) : (
        <span className="faint">—</span>
      ),
  },
  {
    key: 'confidence',
    header: '置信度',
    align: 'right',
    render: (row) => (
      <span className="mono" style={{ color: row.pii_confidence >= 0.5 ? 'var(--ink)' : 'var(--ink-faint)' }}>
        {row.pii_type ? row.pii_confidence.toFixed(3) : '—'}
      </span>
    ),
  },
  {
    key: 'null',
    header: '空值率',
    align: 'right',
    render: (row) => <span className="mono faint">{formatPercent(row.null_ratio)}</span>,
  },
  {
    key: 'sample',
    header: '样例值',
    render: (row) => (
      <span className="mono faint" style={{ fontSize: 11.5 }}>
        {row.sample_values.slice(0, 2).join(' ／ ') || '—'}
      </span>
    ),
  },
];

export const DatasetProfilePage = () => {
  const navigate = useNavigate();
  const {
    tables,
    selectedTableId,
    detail,
    loading,
    scanning,
    error,
    lastScan,
    loadTables,
    selectTable,
    scan,
  } = useDatasetStore();
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!tables.length) void loadTables();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleScan = async () => {
    const result = await scan();
    if (result) {
      const idCard = result.findings_detail.find((finding) => finding.pii_type === 'id_card');
      setScanMessage(
        idCard
          ? `${result.message}；身份证列命中 ${idCard.matched_count} 条，校验位通过 ${idCard.checksum_pass_count} 条`
          : result.message,
      );
    }
  };

  return (
    <>
      <SectionHead
        kicker="01 / DATASET PROFILE"
        title="数据集与列画像"
        description="三张上游表登记在案。选一张表看列级画像：类型、角色、敏感度热力，以及 PII 命中与置信度。点击任意列进入证据页。"
        actions={
          <RoleGate
            permission="datasets:scan"
            fallback={<span className="faint" style={{ fontSize: 11.5 }}>client 只读，不能重跑扫描</span>}
          >
            <button className="btn btn-stamp" type="button" onClick={handleScan} disabled={scanning || !selectedTableId}>
              {scanning ? '扫描中…' : '重新扫描 PII'}
            </button>
          </RoleGate>
        }
      />

      {error ? <div className="notice section">{error}</div> : null}
      {scanMessage ? (
        <div className="notice notice-ok section">
          {scanMessage}（耗时 {lastScan?.duration_ms ?? 0} ms，算法 {lastScan?.findings_detail[0]?.algorithm_version ?? 'pii-1.0'}）
        </div>
      ) : null}
      {lastScan ? null : null}

      <div className="section">
        <div className="kicker" style={{ marginBottom: 8 }}>
          卷内数据集 / 点击切换
        </div>
        <div className="grid-3">
          {tables.map((table) => (
            <button
              key={table.id}
              type="button"
              onClick={() => void selectTable(table.id)}
              style={{
                textAlign: 'left',
                background: table.id === selectedTableId ? 'var(--paper-raised)' : 'transparent',
                border: '1px solid var(--rule)',
                borderLeft:
                  table.id === selectedTableId ? '3px solid var(--stamp)' : '1px solid var(--rule)',
                padding: '12px 14px',
                transition: 'background-color 140ms ease',
              }}
            >
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <span className="display-sm" style={{ fontSize: 16, fontWeight: 700 }}>
                  {table.display_name}
                </span>
                <SensitivityBar level={table.sensitivity_level} showLabel={false} />
              </div>
              <div className="mono faint" style={{ fontSize: 11, marginTop: 2 }}>
                clinic.{table.table_name}
              </div>
              <div className="row" style={{ marginTop: 8, gap: 10, fontSize: 11.5 }}>
                <span className="num">{formatNumber(table.row_count)} 行</span>
                <span className="faint">{table.column_count} 列</span>
                <span style={{ color: table.pii_column_count ? 'var(--stamp-deep)' : 'var(--ink-faint)' }}>
                  PII {table.pii_column_count} 列
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {loading && !detail ? (
        <EmptyState title="正在翻开卷宗…" hint="读取列画像与 PII 扫描结果。" />
      ) : detail ? (
        <>
          <div className="section">
            <StatStrip
              items={[
                { label: '数据行', value: formatNumber(detail.table.row_count) },
                { label: '列数', value: detail.table.column_count },
                { label: 'PII 列', value: detail.pii_summary.finding_count, tone: 'stamp' },
                { label: '命中值', value: formatNumber(detail.pii_summary.total_matched), tone: 'stamp' },
                {
                  label: '校验位通过',
                  value: `${detail.pii_summary.checksum_passed}/${detail.pii_summary.checksum_checked}`,
                  tone: 'amber',
                },
                { label: '敏感级别', value: SENSITIVITY_LABELS[detail.table.sensitivity_level], tone: 'amber' },
              ]}
            />
          </div>

          <div className="section">
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
              <h3 className="subhead" style={{ borderBottom: 0, paddingBottom: 0, marginBottom: 0 }}>
                列画像 · {detail.table.display_name}
              </h3>
              <div className="row" style={{ gap: 10 }}>
                <StickerTag label={detail.table.business_domain} />
                {detail.table.last_profiled_at ? (
                  <span className="faint" style={{ fontSize: 11 }}>
                    上次扫描 {detail.table.last_profiled_at.slice(0, 16).replace('T', ' ')}
                  </span>
                ) : (
                  <StampBadge tone="warn" rotate={-2}>
                    未扫描
                  </StampBadge>
                )}
              </div>
            </div>
            <div className="panel">
              <ArchiveTable
                columns={tableColumns}
                rows={detail.columns}
                rowKey={(row) => row.id}
                onRowClick={(row) =>
                  navigate(`/pii-evidence?table=${row.table_id}&column=${row.id}`)
                }
              />
            </div>
            <p className="faint" style={{ fontSize: 11.5, marginTop: 8 }}>
              敏感度热力：低 → 中 → 高 → 极高；置信度 = 命中率 × 校验位通过率 × (1 − 唯一性惩罚)。
            </p>
          </div>
        </>
      ) : (
        <EmptyState title="还没有选中的数据集" hint="先在上方选择一张表，或重新扫描 PII 生成画像。" />
      )}
    </>
  );
};

export type { DatasetTable };
