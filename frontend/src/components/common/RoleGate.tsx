import type { ReactNode } from 'react';
import { useAuthStore } from '../../stores/authStore';
import type { Permission } from '../../constants/rbac';

interface Props {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
}

/** 权限门：前端只做提示与隐藏，真正的 403 由后端权限点保证。 */
export const RoleGate = ({ permission, children, fallback }: Props) => {
  const can = useAuthStore((state) => state.can);
  if (can(permission)) return <>{children}</>;
  return (
    <>
      {fallback ?? (
        <div className="notice notice-warn">
          当前角色没有「{permission}」权限，只能查看。切换 admin / dpo 账号可执行该操作。
        </div>
      )}
    </>
  );
};
