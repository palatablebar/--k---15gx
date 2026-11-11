import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { NAV_ITEMS } from '../../constants/nav';
import { ACTOR_ROLE_LABELS } from '../../constants/enums';
import { useAuthStore } from '../../stores/authStore';

/** 档案工作台外壳：页眉卷宗号 + 左侧编号目录 + 右侧纸张正文。 */
export const ArchiveShell = () => {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="shell">
      <header className="masthead">
        <div className="masthead-mark">
          <span className="stamp" style={{ transform: 'rotate(-6deg)', animation: 'none' }}>
            MASKGUARD
          </span>
          <div>
            <div className="masthead-title">脱敏与 k-匿名合规工作台</div>
            <div className="masthead-sub">
              云诊 · 合规数据服务组 ／ 卷宗 2026-11 ／ 上游 clinic 库 3 张表
            </div>
          </div>
        </div>
        <div className="masthead-user">
          <span className="role-chip">{user ? ACTOR_ROLE_LABELS[user.role] ?? user.role : '未登录'}</span>
          <span className="user-name">{user?.display_name ?? '—'}</span>
          <span className="faint">{user?.email}</span>
          <button type="button" className="btn-quiet" onClick={handleLogout}>
            注销
          </button>
        </div>
      </header>
      <div className="shell-body">
        <nav className="rail" aria-label="工作台目录">
          <div className="rail-index">目录 / CONTENTS</div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-no">{item.index}</span>
              <span>
                <span className="nav-label">{item.label}</span>
                <span className="nav-hint">{item.hint}</span>
              </span>
            </NavLink>
          ))}
          <div className="rail-foot">
            算法版本
            <br />
            PII pii-1.0 ／ k-匿名 kanon-1.0
            <br />
            年龄基准日 2026-11-10
          </div>
        </nav>
        <main className="sheet">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
