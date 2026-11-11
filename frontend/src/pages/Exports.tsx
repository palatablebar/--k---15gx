import { useEffect, useState } from 'react';
import { datasetApi } from '../api/datasets';
import { exportApi } from '../api/exports';
import { useExportStore } from '../stores/exportStore';
import { useAuthStore } from '../stores/authStore';
import { SectionHead } from '../components/common/SectionHead';
import { StampBadge } from '../components/common/StampBadge';
import { EmptyState } from '../components/common/EmptyState';
import { StatStrip } from '../components/common/StatStrip';
import { formatDate, formatNumber, shortId } from '../utils/format';
import { BUILD_STATUS_LABELS, EXPORT_STATUS_LABELS, GATE_STATUS_LABELS } from '../constants/enums';
import type { DatasetTable, ExportRequest } from '../types/models';

const statusTone = (status: ExportRequest['status']) =>
  status === 'approved' ? 'ok' : status === 'rejected' ? 'stamp' : 'warn';

/** 门禁徽标：未校验不显示；结论失效优先于达标/拦截（规则或数据已变化）。 */
const gateView = (item: ExportRequest) => {
  const gate = item.gate;
  if (gate.status === 'unchecked') return null;
  if (gate.stale) return { tone: 'warn' as const, label: '门禁结论已失效' };
  if (gate.status === 'passed') return { tone: 'ok' as const, label: GATE_STATUS_LABELS.passed };
  return { tone: 'stamp' as const, label: `${GATE_STATUS_LABELS.blocked} · ${gate.gaps.length} 项` };
};

export const ExportsPage = () => {
  const can = useAuthStore((state) => state.can);
  const user = useAuthStore((state) => state.user);
  const { items, loading, busyId, error, load, submit, precheck, approve, reject } = useExportStore();
  const [tables, setTables] = useState<DatasetTable[]>([]);
  const [tableId, setTableId] = useState('');
  const [purpose, setPurpose] = useState('心研所 12 月随访分析，仅需去标识行级数据，伦理批件 YZ-2026-131。');
  const [rows, setRows] = useState(800);
  const [note, setNote] = useState('用途与伦理批件齐全，按策略脱敏后放行。');
  const [formMessage, setFormMessage] = useState<string | null>(null);

  useEffect(() => {
    void load();
    void (async () => {
      const response = await datasetApi.list();
      setTables(response.items);
      const patients = response.items.find((table) => table.table_name === 'patients') ?? response.items[0];
      if (patients) setTableId(patients.id);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormMessage(null);
    const ok = await submit({ table_id: tableId, purpose, requested_rows: rows });
    if (ok) setFormMessage('导出申请已提交，等待 admin / dpo 审批。');
  };

  const handlePrecheck = async (requestId: string) => {
    setFormMessage(null);
    const ok = await precheck(requestId);
    if (ok) setFormMessage('合规校验完成，结论与缺口已写入台账（规则或数据变化后需重新校验）。');
  };

  const handleApprove = async (requestId: string) => {
    setFormMessage(null);
    const ok = await approve(requestId, note);
    if (ok) setFormMessage('门禁达标，已批准；worker 正在生成脱敏 CSV 并计算 sha256 摘要。');
  };

  const handleReject = async (requestId: string) => {
    setFormMessage(null);
    const ok = await reject(requestId, note || '材料不全，请补充后重新提交。');
    if (ok) setFormMessage('已驳回，审批意见写入台账。');
  };

  const pending = items.filter((item) => item.status === 'pending').length;

  return (
    <>
      <SectionHead
        kicker="05 / EXPORT LEDGER"
        title="导出申请与审批台账"
        description="谁申请、什么用途、谁批的、文件摘要多少，全部留在台账里。批准前强制过合规门禁：直接标识列必须全部配有生效策略，k-匿名校验必须达标且覆盖当前导出范围；规则或数据一变，旧结论自动失效。"
      />

      {error ? (
        <div className="notice section" style={{ whiteSpace: 'pre-line' }}>
          {error}
        </div>
      ) : null}
      {formMessage ? <div className="notice notice-ok section">{formMessage}</div> : null}

      <div className="section">
        <StatStrip
          items={[
            { label: '申请总数', value: items.length },
            { label: '待审批', value: pending, tone: 'amber' },
            { label: '已批准', value: items.filter((item) => item.status === 'approved').length, tone: 'olive' },
            { label: '已驳回', value: items.filter((item) => item.status === 'rejected').length, tone: 'stamp' },
            { label: '当前角色', value: user?.role ?? '—' },
          ]}
        />
      </div>

      <div className="grid-2 section" style={{ alignItems: 'start' }}>
        <form className="panel panel-pad" onSubmit={handleSubmit}>
          <div className="subhead">提交导出申请</div>
          <label className="field" style={{ marginBottom: 10 }}>
            <span className="field-label">数据集</span>
            <select className="select" value={tableId} onChange={(event) => setTableId(event.target.value)}>
              {tables.map((table) => (
                <option value={table.id} key={table.id}>
                  {table.display_name}（clinic.{table.table_name}）
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ marginBottom: 10 }}>
            <span className="field-label">用途说明（与研究伦理批件对应）</span>
            <textarea className="textarea" value={purpose} onChange={(event) => setPurpose(event.target.value)} />
          </label>
          <label className="field" style={{ marginBottom: 12 }}>
            <span className="field-label">申请行数</span>
            <input
              className="input num"
              type="number"
              min={1}
              max={5000}
              value={rows}
              onChange={(event) => setRows(Number(event.target.value))}
            />
          </label>
          <button className="btn btn-stamp" type="submit" disabled={!tableId || purpose.trim().length < 6}>
            提交申请
          </button>
          <p className="faint" style={{ fontSize: 11, marginTop: 10 }}>
            提交后进入待审批；批准与驳回只有 admin / dpo 能执行，审批意见会随台账保留。
          </p>
        </form>

        <div className="panel panel-pad">
          <div className="subhead">审批操作台</div>
          {can('exports:approve') ? (
            <>
              <label className="field">
                <span className="field-label">审批备注</span>
                <textarea className="textarea" value={note} onChange={(event) => setNote(event.target.value)} />
              </label>
              <p className="faint" style={{ fontSize: 11, marginTop: 10 }}>
                「校验」按当前导出范围与现行策略重估门禁并列出缺口；「批准」只在门禁达标时放行，
                被拦截的申请补齐缺口（配策略 / 重跑 k-匿名校验）后可重新校验再批。
              </p>
            </>
          ) : (
            <div className="notice">
              client 只能提交申请与查看状态，审批动作由 admin / dpo 完成（后端权限点 exports:approve）。
            </div>
          )}
        </div>
      </div>

      <div className="section">
        <div className="kicker" style={{ marginBottom: 8 }}>
          台账 / {items.length} 条
        </div>
        <div className="panel">
          {loading && !items.length ? (
            <div className="panel-pad faint">加载台账…</div>
          ) : items.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ width: 64 }}>编号</th>
                    <th>数据集</th>
                    <th>申请人</th>
                    <th>用途</th>
                    <th style={{ width: 60 }} className="right">
                      行数
                    </th>
                    <th style={{ width: 176 }}>状态 / 门禁</th>
                    <th style={{ width: 150 }}>文件摘要</th>
                    <th style={{ width: 118 }}>提交时间</th>
                    <th style={{ width: 150 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const gate = gateView(item);
                    return (
                    <tr key={item.id}>
                      <td className="mono faint">{shortId(item.id)}</td>
                      <td>
                        <div className="mono">{item.table_name}</div>
                        <div className="faint" style={{ fontSize: 10.5 }}>
                          {item.dataset_version}
                        </div>
                      </td>
                      <td>
                        <div>{item.requester_name}</div>
                        <div className="faint" style={{ fontSize: 10.5 }}>
                          {item.requester_email}
                        </div>
                      </td>
                      <td className="muted" style={{ fontSize: 11.5, maxWidth: 260 }}>
                        {item.purpose}
                      </td>
                      <td className="right mono">{formatNumber(item.requested_rows)}</td>
                      <td>
                        <StampBadge tone={statusTone(item.status)} rotate={-2}>
                          {EXPORT_STATUS_LABELS[item.status]}
                        </StampBadge>
                        <div className="faint" style={{ fontSize: 10, marginTop: 3 }}>
                          {BUILD_STATUS_LABELS[item.build_status]}
                        </div>
                        {gate ? (
                          <div style={{ marginTop: 4 }}>
                            <StampBadge tone={gate.tone} rotate={1}>
                              {gate.label}
                            </StampBadge>
                          </div>
                        ) : (
                          <div className="faint" style={{ fontSize: 10, marginTop: 4 }}>
                            门禁：{GATE_STATUS_LABELS.unchecked}
                          </div>
                        )}
                        {item.gate.stale ? (
                          <div className="faint" style={{ fontSize: 10, marginTop: 3, maxWidth: 150 }}>
                            规则或数据已变化，需重新校验
                          </div>
                        ) : null}
                        {item.gate.gaps.length > 0 && !item.gate.stale ? (
                          <ul style={{ margin: '4px 0 0', paddingLeft: 14, maxWidth: 170 }}>
                            {item.gate.gaps.map((gap, index) => (
                              <li
                                key={`${gap.code}-${index}`}
                                style={{ fontSize: 10, color: 'var(--stamp)', lineHeight: 1.5 }}
                              >
                                {gap.message}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </td>
                      <td className="mono faint" style={{ fontSize: 10.5 }}>
                        {item.file_digest ? `${item.file_digest.slice(0, 14)}…` : '—'}
                        {item.masked_rows !== null ? (
                          <div className="faint">{formatNumber(item.masked_rows)} 行已脱敏</div>
                        ) : null}
                      </td>
                      <td className="mono faint" style={{ fontSize: 10.5 }}>
                        {formatDate(item.created_at)}
                      </td>
                      <td>
                        <div className="row" style={{ gap: 4 }}>
                          {can('exports:approve') && item.status === 'pending' ? (
                            <>
                              <button
                                className="btn"
                                type="button"
                                style={{ padding: '3px 8px', fontSize: 11 }}
                                disabled={busyId === item.id}
                                onClick={() => void handlePrecheck(item.id)}
                              >
                                校验
                              </button>
                              <button
                                className="btn"
                                type="button"
                                style={{ padding: '3px 8px', fontSize: 11 }}
                                disabled={busyId === item.id}
                                onClick={() => void handleApprove(item.id)}
                              >
                                批准
                              </button>
                              <button
                                className="btn"
                                type="button"
                                style={{ padding: '3px 8px', fontSize: 11 }}
                                disabled={busyId === item.id}
                                onClick={() => void handleReject(item.id)}
                              >
                                驳回
                              </button>
                            </>
                          ) : null}
                          {item.status === 'approved' && item.build_status === 'done' ? (
                            <a
                              className="btn"
                              style={{ padding: '3px 8px', fontSize: 11 }}
                              href={exportApi.downloadUrl(item.id)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              下载 CSV
                            </a>
                          ) : null}
                        </div>
                        {item.review_note ? (
                          <div className="faint" style={{ fontSize: 10.5, marginTop: 4, maxWidth: 200 }}>
                            审批：{item.review_note}
                          </div>
                        ) : null}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="台账还是空的" hint="用左侧表单提交第一条导出申请。" />
          )}
        </div>
      </div>
    </>
  );
};
