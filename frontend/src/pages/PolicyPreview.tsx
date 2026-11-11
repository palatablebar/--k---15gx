import { useEffect } from 'react';
import { usePolicyStore } from '../stores/policyStore';
import { useAuthStore } from '../stores/authStore';
import { SectionHead } from '../components/common/SectionHead';
import { StampBadge } from '../components/common/StampBadge';
import { StickerTag } from '../components/common/StickerTag';
import { RedlineValue } from '../components/common/RedlineValue';
import { StatStrip } from '../components/common/StatStrip';
import { EmptyState } from '../components/common/EmptyState';
import { MASK_METHOD_LABELS } from '../constants/enums';
import { formatNumber, methodParamText } from '../utils/format';

export const PolicyPreviewPage = () => {
  const { policies, selectedId, preview, loading, previewing, error, load, select, runPreview } =
    usePolicyStore();
  const can = useAuthStore((state) => state.can);
  const selected = policies.find((policy) => policy.id === selectedId) ?? null;

  useEffect(() => {
    void (async () => {
      await load();
      if (useAuthStore.getState().can('policies:preview')) {
        await runPreview();
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelect = async (policyId: string) => {
    select(policyId);
    if (can('policies:preview')) {
      // 选择后立即给一次真实预览
      setTimeout(() => void runPreview(), 0);
    }
  };

  return (
    <>
      <SectionHead
        kicker="03 / MASKING POLICIES"
        title="掩码策略与预览"
        description="五条策略覆盖 mask / hash / generalize / suppress 四种方法。预览会真实读取原始列，逐值套用后给出前后对照与区分度变化——不是前端假图。"
        actions={
          <button
            className="btn btn-stamp"
            type="button"
            disabled={!can('policies:preview') || !selectedId || previewing}
            onClick={() => void runPreview()}
          >
            {previewing ? '预览计算中…' : can('policies:preview') ? '重新预览' : '无预览权限'}
          </button>
        }
      />

      {error ? <div className="notice section">{error}</div> : null}

      <div className="grid-2 section" style={{ alignItems: 'start' }}>
        <div>
          <div className="kicker" style={{ marginBottom: 8 }}>
            策略册 / {policies.length} 条
          </div>
          <div className="stack" style={{ gap: 5 }}>
            {policies.map((policy) => (
              <button
                key={policy.id}
                type="button"
                onClick={() => void handleSelect(policy.id)}
                style={{
                  textAlign: 'left',
                  background: policy.id === selectedId ? 'var(--paper-raised)' : 'transparent',
                  border: '1px solid var(--rule)',
                  borderLeft:
                    policy.id === selectedId ? '3px solid var(--stamp)' : '1px solid var(--rule)',
                  padding: '10px 12px',
                }}
              >
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 600 }}>{policy.name}</span>
                  <StickerTag
                    label={MASK_METHOD_LABELS[policy.method]}
                    tone={policy.method === 'suppress' ? 'red' : 'plain'}
                    rotate={1.2}
                  >
                    {policy.column_pattern}
                  </StickerTag>
                </div>
                <div className="mono faint" style={{ fontSize: 11, marginTop: 3 }}>
                  {policy.table_name ? `clinic.${policy.table_name}` : '全部数据集'} ／{' '}
                  {methodParamText(policy.params)}
                </div>
              </button>
            ))}
            {!policies.length && !loading ? (
              <EmptyState title="还没有策略" hint="由 admin 在策略册里新建掩码策略。" />
            ) : null}
          </div>
        </div>

        <div className="stack">
          {selected ? (
            <div className="panel panel-stack panel-pad">
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="kicker">
                    {selected.table_name ? `clinic.${selected.table_name}` : '全部数据集'} ／ 列通配{' '}
                    {selected.column_pattern}
                  </div>
                  <h3 className="display" style={{ fontSize: 23, marginTop: 2 }}>
                    {selected.name}
                  </h3>
                </div>
                <StampBadge rotate={-5}>{MASK_METHOD_LABELS[selected.method]}</StampBadge>
              </div>
              <p className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>
                {selected.description}
              </p>
              <div className="row" style={{ marginTop: 10, gap: 8 }}>
                <StickerTag label={methodParamText(selected.params)} rotate={-1.4} />
                <StickerTag label={selected.is_active ? '生效中' : '已停用'} rotate={1.8} />
                {selected.pii_type ? <StickerTag label={`PII ${selected.pii_type}`} tone="red" /> : null}
              </div>
            </div>
          ) : null}

          {preview ? (
            <>
              <StatStrip
                items={[
                  { label: '处理值数', value: formatNumber(preview.total_rows) },
                  { label: '命中列', value: preview.applied_columns.length, tone: 'stamp' },
                  {
                    label: '实际变化值',
                    value: formatNumber(
                      preview.applied_columns.reduce((sum, column) => sum + column.changed_rows, 0),
                    ),
                    tone: 'amber',
                  },
                  { label: '信息损失提示', value: preview.method === 'suppress' ? '最高' : '可控' },
                ]}
              />
              {preview.warnings.map((warning) => (
                <div className="notice notice-warn" key={warning}>
                  {warning}
                </div>
              ))}
              {preview.applied_columns.map((column) => (
                <div className="panel panel-pad" key={column.column_id}>
                  <div className="row" style={{ justifyContent: 'space-between' }}>
                    <h4 className="subhead" style={{ borderBottom: 0, marginBottom: 0, paddingBottom: 0 }}>
                      列 <span className="mono">{column.column_name}</span>
                    </h4>
                    <div className="row faint" style={{ fontSize: 11 }}>
                      <span>区分度 {column.distinct_before} → {column.distinct_after}</span>
                      <span>变化 {formatNumber(column.changed_rows)} / {formatNumber(column.total_rows)}</span>
                    </div>
                  </div>
                  <div className="stack" style={{ marginTop: 8, gap: 4 }}>
                    {column.samples.map((sample, index) => (
                      <div className="mono" style={{ fontSize: 12 }} key={`${column.column_id}-${index}`}>
                        <RedlineValue before={sample.before} after={sample.after} span={sample.removable_span} />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </>
          ) : loading || previewing ? (
            <EmptyState title="正在读原始列做预览…" hint="逐值套用策略并统计区分度变化。" />
          ) : (
            <EmptyState
              title="选择一条策略查看预览"
              hint="预览会读取原始列（最多 800 行）并逐值应用掩码方法。"
            />
          )}
        </div>
      </div>
    </>
  );
};
