import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { piiApi, type ColumnEvidenceResponse } from '../api/pii';
import type { PiiFinding } from '../types/models';
import { SectionHead } from '../components/common/SectionHead';
import { StampBadge } from '../components/common/StampBadge';
import { StickerTag } from '../components/common/StickerTag';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import { RedlineValue } from '../components/common/RedlineValue';
import { StatStrip } from '../components/common/StatStrip';
import { EmptyState } from '../components/common/EmptyState';
import { SensitivityBar } from '../components/common/SensitivityBar';
import { PII_TYPE_LABELS, COLUMN_ROLE_LABELS } from '../constants/enums';
import { formatPercent } from '../utils/format';
import { errorMessage } from '../utils/format';

export const PiiEvidencePage = () => {
  const [params, setParams] = useSearchParams();
  const [findings, setFindings] = useState<PiiFinding[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<ColumnEvidenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await piiApi.findings();
        if (cancelled) return;
        setFindings(response.items);
        const requested = params.get('column');
        const preferred =
          (requested && response.items.find((item) => item.column_id === requested)?.column_id) ||
          response.items.find((item) => item.pii_type === 'id_card')?.column_id ||
          response.items[0]?.column_id ||
          null;
        setSelectedId(preferred);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const response = await piiApi.columnEvidence(selectedId);
        if (!cancelled) {
          setEvidence(response);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const handleSelect = (finding: PiiFinding) => {
    setSelectedId(finding.column_id);
    setParams({ table: finding.table_id, column: finding.column_id }, { replace: true });
  };

  const detail = evidence?.finding;
  const table = evidence?.table;
  const column = evidence?.column;

  return (
    <>
      <SectionHead
        kicker="02 / PII EVIDENCE"
        title="PII 证据与校验位"
        description="每一列只给出一个胜出的 PII 类型，但会保留完整的置信度拆解：命中率、校验位通过率、唯一性惩罚。证据样例里能逐条看到校验位是否通过。"
      />

      {error ? <div className="notice section">{error}</div> : null}

      <div className="grid-2 section" style={{ alignItems: 'start' }}>
        <div>
          <div className="kicker" style={{ marginBottom: 8 }}>
            命中列清单 / {findings.length} 条证据
          </div>
          <div className="stack" style={{ gap: 5 }}>
            {findings.map((finding) => (
              <button
                key={finding.id}
                type="button"
                onClick={() => handleSelect(finding)}
                style={{
                  textAlign: 'left',
                  background: finding.column_id === selectedId ? 'var(--paper-raised)' : 'transparent',
                  border: '1px solid var(--rule)',
                  borderLeft:
                    finding.column_id === selectedId
                      ? '3px solid var(--stamp)'
                      : '1px solid var(--rule)',
                  padding: '9px 12px',
                }}
              >
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <span className="mono" style={{ fontWeight: 600 }}>
                    {finding.table_name}.{finding.column_name}
                  </span>
                  <StickerTag label={PII_TYPE_LABELS[finding.pii_type]} tone="red" rotate={1.4}>
                    {finding.matched_count} 命中
                  </StickerTag>
                </div>
                <div className="row faint" style={{ marginTop: 4, fontSize: 11, gap: 10 }}>
                  <span>置信 {finding.confidence.toFixed(3)}</span>
                  <span>候选 {finding.candidate_rows}</span>
                  <span>校验 {finding.checksum_pass_count}/{finding.checksum_checked_count}</span>
                </div>
              </button>
            ))}
            {!findings.length && !loading ? (
              <EmptyState title="还没有 PII 证据" hint="到「数据集与列画像」页执行一次重新扫描。" />
            ) : null}
          </div>
        </div>

        {detail && table && column ? (
          <div className="stack">
            <div className="panel panel-stack panel-pad">
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="kicker">
                    {table.display_name} ／ clinic.{table.table_name}
                  </div>
                  <h3 className="display" style={{ fontSize: 26, marginTop: 2 }}>
                    {column.name}
                  </h3>
                  <div className="row" style={{ marginTop: 6, gap: 8 }}>
                    <StickerTag label={`类型 ${column.data_type}`} rotate={-1.2} />
                    <StickerTag label={COLUMN_ROLE_LABELS[column.column_role]} rotate={1.6} />
                    <SensitivityBar level={column.sensitivity_level} />
                  </div>
                </div>
                <StampBadge rotate={-7}>{PII_TYPE_LABELS[detail.pii_type]}</StampBadge>
              </div>

              <div style={{ marginTop: 16 }}>
                <StatStrip
                  items={[
                    { label: '命中', value: detail.matched_count, tone: 'stamp' },
                    { label: '候选值', value: detail.candidate_rows },
                    { label: '校验通过', value: `${detail.checksum_pass_count}/${detail.checksum_checked_count}`, tone: 'amber' },
                    { label: '唯一性惩罚', value: detail.uniqueness_penalty.toFixed(2) },
                    { label: '置信度', value: detail.confidence.toFixed(4), tone: 'stamp' },
                  ]}
                />
              </div>

              <div style={{ marginTop: 14 }}>
                <ConfidenceMeter
                  label="列级置信度"
                  value={detail.confidence}
                  caption={`命中率 ${formatPercent(detail.hit_rate)} × 校验通过率 ${formatPercent(
                    detail.checksum_pass_rate,
                  )} × (1 − 唯一性惩罚 ${detail.uniqueness_penalty.toFixed(2)}) ／ 算法 ${detail.algorithm_version}`}
                />
              </div>
            </div>

            <div className="panel panel-pad">
              <div className="subhead">证据样例（红线为命中/校验失败区段）</div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ width: 44 }}>#</th>
                      <th>原始值</th>
                      <th style={{ width: 96 }}>校验结果</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.evidence.map((sample, index) => (
                      <tr key={`${sample.kind}-${index}-${sample.value}`}>
                        <td className="mono faint">{String(index + 1).padStart(2, '0')}</td>
                        <td>
                          {sample.kind === 'match' ? (
                            <RedlineValue
                              before={sample.value}
                              after="[已命中]"
                              span={[sample.span_start, sample.span_end]}
                            />
                          ) : (
                            <span className="mono faint">{sample.value}</span>
                          )}
                        </td>
                        <td>
                          {sample.validation === 'passed' ? (
                            <StampBadge tone="ok" rotate={-2}>
                              通过
                            </StampBadge>
                          ) : sample.validation === 'failed' ? (
                            <StampBadge tone="stamp" rotate={2}>
                              不通过
                            </StampBadge>
                          ) : (
                            <span className="faint">—</span>
                          )}
                        </td>
                        <td className="faint">{sample.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="faint" style={{ fontSize: 11.5, marginTop: 10 }}>
                列样例值：{column.sample_values.slice(0, 4).join(' ／ ')}
              </p>
            </div>
          </div>
        ) : loading ? (
          <EmptyState title="正在比对证据…" hint="读取列样例与校验位结果。" />
        ) : null}
      </div>
    </>
  );
};
