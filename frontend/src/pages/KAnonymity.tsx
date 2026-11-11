import { useEffect, useMemo, useState } from 'react';
import { datasetApi } from '../api/datasets';
import { useKanonStore } from '../stores/kanonStore';
import { useAuthStore } from '../stores/authStore';
import { useCheckPolling } from '../hooks/useCheckPolling';
import { SectionHead } from '../components/common/SectionHead';
import { StampBadge } from '../components/common/StampBadge';
import { StickerTag } from '../components/common/StickerTag';
import { StatStrip } from '../components/common/StatStrip';
import { ArchiveTable, type ArchiveColumn } from '../components/common/ArchiveTable';
import { EmptyState } from '../components/common/EmptyState';
import { COLUMN_ROLE_LABELS } from '../constants/enums';
import { formatNumber } from '../utils/format';
import type { DatasetColumn, DatasetTable, KanonCandidate } from '../types/models';

const candidateColumns: ArchiveColumn<KanonCandidate>[] = [
  {
    key: 'levels',
    header: '泛化层级',
    render: (row) => (
      <span className="mono" style={{ fontSize: 11.5 }}>
        {Object.entries(row.level_labels)
          .map(([key, label]) => `${key}→${label}`)
          .join(' ／ ')}
      </span>
    ),
  },
  { key: 'k', header: 'k', align: 'right', render: (row) => <span className="mono">{row.k}</span> },
  { key: 'l', header: 'ℓ', align: 'right', render: (row) => <span className="mono">{row.l}</span> },
  {
    key: 'classes',
    header: '等价类',
    align: 'right',
    render: (row) => <span className="mono faint">{row.class_count}</span>,
  },
  {
    key: 'loss',
    header: '信息损失',
    align: 'right',
    render: (row) => <span className="mono">{row.information_loss.toFixed(3)}</span>,
  },
  {
    key: 'passed',
    header: '结论',
    render: (row) =>
      row.passed ? (
        <StampBadge tone="ok" rotate={-2}>
          达标
        </StampBadge>
      ) : (
        <span className="faint" style={{ fontSize: 11 }}>
          不达标
        </span>
      ),
  },
];

export const KAnonymityPage = () => {
  const can = useAuthStore((state) => state.can);
  const { checks, current, running, error, load, run, refreshCurrent, setCurrent } = useKanonStore();
  const [tables, setTables] = useState<DatasetTable[]>([]);
  const [columns, setColumns] = useState<DatasetColumn[]>([]);
  const [tableId, setTableId] = useState<string>('');
  const [selectedQi, setSelectedQi] = useState<string[]>(['birth_date', 'gender', 'zip']);
  const [sensitive, setSensitive] = useState<string>('diagnosis');
  const [targetK, setTargetK] = useState<number>(5);
  const [targetL, setTargetL] = useState<number>(2);
  const [formError, setFormError] = useState<string | null>(null);

  useCheckPolling(current, refreshCurrent);

  useEffect(() => {
    void load();
    void (async () => {
      const response = await datasetApi.list();
      setTables(response.items);
      const patients = response.items.find((table) => table.table_name === 'patients') ?? response.items[0];
      if (patients) {
        setTableId(patients.id);
        const detail = await datasetApi.detail(patients.id);
        setColumns(detail.columns);
        const sensitiveColumn = detail.columns.find((column) => column.column_role === 'sensitive');
        if (sensitiveColumn) setSensitive(sensitiveColumn.name);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const qiOptions = useMemo(
    () => columns.filter((column) => column.column_role === 'quasi_id'),
    [columns],
  );
  const sensitiveOptions = useMemo(
    () => columns.filter((column) => column.column_role === 'sensitive'),
    [columns],
  );

  const histogram = current?.class_size_histogram ?? {};
  const histogramMax = Math.max(1, ...Object.values(histogram));
  const equivalence = current?.equivalence_classes ?? [];

  const handleRun = async () => {
    setFormError(null);
    if (selectedQi.length < 2) {
      setFormError('至少选择 2 个准标识列');
      return;
    }
    const result = await run({
      table_id: tableId,
      quasi_identifiers: selectedQi,
      sensitive_column: sensitive,
      target_k: targetK,
      target_l: targetL,
    });
    if (result && result.status === 'failed') {
      setFormError(result.error_detail ?? '计算失败');
    }
  };

  const toggleQi = (name: string) => {
    setSelectedQi((prev) =>
      prev.includes(name) ? prev.filter((item) => item !== name) : [...prev, name],
    );
  };

  return (
    <>
      <SectionHead
        kicker="04 / K-ANONYMITY"
        title="k-匿名 / ℓ-diversity 校验"
        description="选准标识组合与敏感属性，计算等价类分布；搜索年龄与邮编的泛化层级组合，在 k≥目标值、ℓ≥目标值的前提下选信息损失最小的方案。worker 异步算，backend 同步兜底。"
        actions={
          can('kanon:run') ? (
            <button className="btn btn-stamp" type="button" onClick={() => void handleRun()} disabled={running || !tableId}>
              {running ? '提交计算…' : '运行校验'}
            </button>
          ) : (
            <span className="faint" style={{ fontSize: 11.5 }}>
              client 只读：不能发起校验（后端返回 403）
            </span>
          )
        }
      />

      {error ? <div className="notice section">{error}</div> : null}
      {formError ? <div className="notice section">{formError}</div> : null}

      <div className="grid-2 section" style={{ alignItems: 'start' }}>
        <div className="panel panel-pad">
          <div className="subhead">准标识选择</div>
          <label className="field" style={{ marginBottom: 10 }}>
            <span className="field-label">数据集</span>
            <select className="select" value={tableId} onChange={(event) => setTableId(event.target.value)}>
              {tables.map((table) => (
                <option value={table.id} key={table.id}>
                  clinic.{table.table_name}（{table.display_name}）
                </option>
              ))}
            </select>
          </label>
          <div className="field" style={{ marginBottom: 10 }}>
            <span className="field-label">准标识列（2–4 个）</span>
            <div className="row" style={{ gap: 6 }}>
              {qiOptions.map((column) => (
                <label className="checkline" key={column.id}>
                  <input
                    type="checkbox"
                    checked={selectedQi.includes(column.name)}
                    onChange={() => toggleQi(column.name)}
                  />
                  <span className="mono">{column.name}</span>
                  <span className="faint" style={{ fontSize: 10 }}>
                    {COLUMN_ROLE_LABELS[column.column_role]}
                  </span>
                </label>
              ))}
              {!qiOptions.length ? <span className="faint">该表没有准标识列</span> : null}
            </div>
          </div>
          <div className="grid-3">
            <label className="field">
              <span className="field-label">敏感属性</span>
              <select className="select" value={sensitive} onChange={(event) => setSensitive(event.target.value)}>
                {sensitiveOptions.map((column) => (
                  <option value={column.name} key={column.id}>
                    {column.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">目标 k</span>
              <input
                className="input num"
                type="number"
                min={2}
                max={50}
                value={targetK}
                onChange={(event) => setTargetK(Number(event.target.value))}
              />
            </label>
            <label className="field">
              <span className="field-label">目标 ℓ</span>
              <input
                className="input num"
                type="number"
                min={1}
                max={10}
                value={targetL}
                onChange={(event) => setTargetL(Number(event.target.value))}
              />
            </label>
          </div>
          <p className="faint" style={{ fontSize: 11, marginTop: 10 }}>
            年龄由 birth_date 与固定基准日 2026-11-10 推导；泛化层级：年龄 1/5/10 岁，邮编 5/3/2 位。
          </p>
        </div>

        <div className="stack">
          {current ? (
            <>
              <div className="panel panel-pad">
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div
                      className="mono"
                      style={{ fontSize: 10.5, letterSpacing: '0.08em', color: 'var(--ink-faint)' }}
                    >
                      {current.table_name} ／ QI {current.quasi_identifiers.join(' + ')} ／ 敏感{' '}
                      {current.sensitive_column}
                    </div>
                    <h3 className="display" style={{ fontSize: 22, marginTop: 2 }}>
                      等价类与泛化建议
                    </h3>
                  </div>
                  {current.status === 'succeeded' ? (
                    <StampBadge tone={current.passed ? 'ok' : 'stamp'} rotate={-6}>
                      {current.passed ? '泛化后达标' : '不达标'}
                    </StampBadge>
                  ) : (
                    <StampBadge tone="warn" rotate={-2}>
                      {current.status === 'failed' ? '计算失败' : '计算中'}
                    </StampBadge>
                  )}
                </div>

                <div style={{ marginTop: 14 }}>
                  <StatStrip
                    items={[
                      { label: '基线 k', value: current.base_k ?? '—', tone: 'stamp' },
                      { label: '基线 ℓ', value: current.base_l ?? '—' },
                      {
                        label: '推荐 k',
                        value: current.final_k ?? '—',
                        tone: current.passed ? 'olive' : 'stamp',
                      },
                      { label: '推荐 ℓ', value: current.final_l ?? '—' },
                      {
                        label: '信息损失',
                        value: current.information_loss !== null ? current.information_loss.toFixed(3) : '—',
                        tone: 'amber',
                      },
                    ]}
                  />
                </div>

                <div className="row" style={{ marginTop: 12, gap: 8 }}>
                  {Object.entries(current.recommended_level.level_labels ?? {}).map(([key, label]) => (
                    <StickerTag key={key} label={`${key} → ${label}`} rotate={-1.2} />
                  ))}
                </div>

                <p className="muted" style={{ marginTop: 12, fontSize: 12.5, lineHeight: 1.75 }}>
                  {current.conclusion}
                </p>
                {current.error_detail ? <div className="notice">{current.error_detail}</div> : null}
              </div>

              <div className="panel panel-pad">
                <div className="subhead">基线等价类规模分布（共 {current.equivalence_classes.length} 个展示）</div>
                <div className="bar-list">
                  {Object.entries(histogram).map(([size, count]) => (
                    <div className="bar-row" key={size}>
                      <span className="mono faint">大小 {size} 行</span>
                      <div className="bar-track">
                        <div
                          className={`bar-fill ${Number(size) < current.target_k ? 'stamp' : ''}`}
                          style={{ width: `${(count / histogramMax) * 100}%` }}
                        />
                      </div>
                      <span className="mono faint">{count} 类</span>
                    </div>
                  ))}
                </div>
                <div className="table-wrap" style={{ marginTop: 14 }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>准标识组合</th>
                        <th style={{ width: 70 }}>行数</th>
                        <th>敏感值</th>
                      </tr>
                    </thead>
                    <tbody>
                      {equivalence.slice(0, 8).map((item, index) => (
                        <tr key={index}>
                          <td className="mono" style={{ fontSize: 11.5 }}>
                            {Object.entries(item.qi)
                              .map(([key, value]) => `${key}=${value}`)
                              .join(' ／ ')}
                          </td>
                          <td className="mono">{item.size}</td>
                          <td className="faint" style={{ fontSize: 11.5 }}>
                            {item.sensitive_values.join('、')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="panel panel-pad">
                <div className="subhead">泛化层级候选（穷举 {current.candidates.length} 组合）</div>
                <ArchiveTable
                  columns={candidateColumns}
                  rows={current.candidates.slice(0, 9)}
                  rowKey={(row) => Object.values(row.levels).join('-')}
                  emptyTitle="没有候选组合"
                  emptyHint="检查准标识列是否可泛化。"
                />
              </div>
            </>
          ) : (
            <EmptyState
              title="还没有校验记录"
              hint="提交一次 k-匿名校验：backend 创建任务，worker 计算等价类与泛化建议。"
            />
          )}
        </div>
      </div>

      <div className="section">
        <div className="kicker" style={{ marginBottom: 8 }}>
          校验历史 / {checks.length} 次
        </div>
        <div className="panel">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>数据集</th>
                  <th>准标识</th>
                  <th style={{ width: 70 }}>目标 k</th>
                  <th style={{ width: 70 }}>基线 k</th>
                  <th style={{ width: 70 }}>推荐 k</th>
                  <th style={{ width: 90 }}>状态</th>
                  <th>发起人</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((check) => (
                  <tr key={check.id} className="row-click" onClick={() => setCurrent(check)}>
                    <td className="mono faint" style={{ fontSize: 11.5 }}>
                      {(check.created_at ?? '').slice(0, 16).replace('T', ' ')}
                    </td>
                    <td className="mono">{check.table_name}</td>
                    <td className="mono" style={{ fontSize: 11.5 }}>
                      {check.quasi_identifiers.join(' + ')}
                    </td>
                    <td className="mono">{check.target_k}</td>
                    <td className="mono" style={{ color: 'var(--stamp-deep)' }}>
                      {check.base_k ?? '—'}
                    </td>
                    <td className="mono">{check.final_k ?? '—'}</td>
                    <td>
                      <StampBadge tone={check.passed ? 'ok' : check.status === 'failed' ? 'warn' : 'muted'} rotate={-2}>
                        {check.status === 'succeeded' ? (check.passed ? '达标' : '不达标') : check.status}
                      </StampBadge>
                    </td>
                    <td className="faint">{check.created_by_email ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
};
