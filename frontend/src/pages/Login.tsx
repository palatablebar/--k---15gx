import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { StampBadge } from '../components/common/StampBadge';

const DEMO_ACCOUNTS = [
  { role: '数据平台管理员 admin', email: 'admin@clinic.local', note: '数据源 / 策略 / 审批' },
  { role: '数据保护官 dpo', email: 'dpo@clinic.local', note: 'PII 复核 / k-匿名 / 审批' },
  { role: '科研客户 client', email: 'client@clinic.local', note: '只读数据集 / 提交导出申请' },
];

export const LoginPage = () => {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const loading = useAuthStore((state) => state.loading);
  const storeError = useAuthStore((state) => state.error);
  const [email, setEmail] = useState('dpo@clinic.local');
  const [password, setPassword] = useState('Demo@2026');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    try {
      await login(email.trim(), password);
      navigate('/datasets', { replace: true });
    } catch {
      setLocalError('登录失败，请确认邮箱与口令（演示口令 Demo@2026）');
    }
  };

  return (
    <div className="login-page">
      <section className="login-left">
        <div className="login-watermark">脱敏</div>
        <div>
          <span className="kicker">云诊 · 合规数据服务组 ／ 卷宗 2026-11</span>
          <h1 className="login-title">
            在数据出门之前，
            <br />
            把 <em>该涂掉的地方</em> 涂掉。
          </h1>
          <div className="login-rule" />
          <p className="login-lede">
            上游业务库有三张表：患者主索引、就诊记录、检验结果。这个工作台负责列画像 → PII 证据 →
            掩码策略 → k-匿名 / ℓ-diversity 校验 → 审批导出，每一步都留审计痕迹。
          </p>
          <div style={{ marginTop: 26 }}>
            <div className="kicker" style={{ marginBottom: 8 }}>
              演示账号（口令统一 Demo@2026）
            </div>
            <div className="account-list">
              {DEMO_ACCOUNTS.map((account) => (
                <div className="account-row" key={account.email}>
                  <span style={{ color: 'var(--stamp-deep)' }}>{account.role}</span>
                  <span>
                    <span className="mono">{account.email}</span>
                    <span className="faint" style={{ marginLeft: 10 }}>
                      {account.note}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="row" style={{ gap: 14 }}>
          <StampBadge rotate={-6}>已脱敏</StampBadge>
          <span className="faint" style={{ fontSize: 11.5 }}>
            GB 11643 校验位 · 等价类 k/ℓ 计算 · sha256 加盐假名
          </span>
        </div>
      </section>

      <section className="login-right">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="kicker">SIGN IN / 签入</div>
          <h2 className="display" style={{ fontSize: 24, marginTop: 6 }}>
            合规工作台登录
          </h2>
          <p className="faint" style={{ fontSize: 12, marginTop: 6 }}>
            账号由数据保护办公室统一发放，登录与导出都会写入审计台账。
          </p>

          <div className="stack" style={{ marginTop: 20 }}>
            <label className="field">
              <span className="field-label">邮箱</span>
              <input
                className="input"
                type="email"
                name="email"
                value={email}
                autoComplete="username"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="dpo@clinic.local"
              />
            </label>
            <label className="field">
              <span className="field-label">口令</span>
              <input
                className="input"
                type="password"
                name="password"
                value={password}
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Demo@2026"
              />
            </label>
            {localError || storeError ? (
              <div className="notice">{localError ?? storeError}</div>
            ) : null}
            <button className="btn btn-stamp" type="submit" disabled={loading} style={{ padding: '9px 16px' }}>
              {loading ? '签入中…' : '签入工作台'}
            </button>
            <div className="faint" style={{ fontSize: 11 }}>
              提示：client 账号可以查看全部证据与校验结果，但不能发起 k-匿名校验或审批导出。
            </div>
          </div>
        </form>
      </section>
    </div>
  );
};
