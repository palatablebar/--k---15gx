# maskguard · 数据脱敏与 k-匿名合规工作台

医疗 SaaS「云诊」的合规数据服务组，向科研客户交付脱敏数据集。上游业务库（`clinic` schema）有三张表：
`patients`（800 行）、`visits`（2400 行）、`labs`（1200 行）。maskguard 负责：列画像 → PII 类型识别与证据 →
掩码策略与预览 → k-匿名 / ℓ-diversity 校验与泛化建议 → 导出申请审批与脱敏文件生成，全程审计留痕。

## 真实场景

- **模拟客户**：云诊（医疗 SaaS）合规数据服务组，4 人；下游是心研所等科研客户与监管审计。
- **现有工作流**：Excel 手删列 + Python 脚本掩码 + 人工复检。
- **最痛的 3 个点**：① 漏脱敏身份证号被客户安全扫描打回；② 全掩码导致数据不可用，且 k-匿名从未验证；
  ③ 每份导出谁申请、谁审批没有台账。
- **本系统替代**：列画像与 PII 证据、4 种掩码策略与真实预览、k-匿名/ℓ-diversity 等价类计算与泛化搜索、
  导出审批台账 + 真实脱敏 CSV 生成。
- **上下游**：上游挂号/就诊/检验库 → maskguard → 下游科研客户（去标识数据集）与监管（审计台账）。

## 角色权限

| 角色 | 账号 | 主要页面 | 权限 |
| --- | --- | --- | --- |
| admin 数据平台管理员 | `admin@clinic.local` | 数据集、策略、台账 | 数据源扫描、策略读写、导出审批、审计 |
| dpo 数据保护官 | `dpo@clinic.local` | PII 证据、k-匿名、台账 | PII 复核、k-匿名校验、导出审批、审计 |
| client 科研客户 | `client@clinic.local` | 数据集（只读）、台账 | 只读数据集/证据、提交导出申请；**不能**发起 k-匿名校验或审批（403） |

口令统一 `Demo@2026`。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
# 5/5 healthy 后，seed 会在 backend 启动时自动执行一次；也可手动重跑（幂等）：
docker compose exec -T backend python -m scripts.seed_demo
```

- 前端：http://localhost:18224
- 后端 OpenAPI：http://localhost:19224/docs
- 数据库：`postgresql://maskguard@localhost:17724/maskguard`

## 核心算法（Python 真算，后端持久化）

1. **PII 类型识别 + 4 种掩码**（`backend/src/services/pii_detector.py`、`masking_service.py`）
   - 手机号：11 位正则 + 工信部号段白名单；身份证：18 位 + GB 11643-1999 加权校验位 + 省级前缀；
     邮箱正则；姓名：姓氏表 + 2–4 汉字；地址：行政区/街道关键词 + 长度。
   - 列级置信度 **= 命中率 × 校验位通过率 × (1 − 唯一性惩罚)**；唯一性惩罚 = 0.2 × 候选值唯一率；
     候选值 = 非空且未被 `*`/X 预掩码的值。命中数 < max(5, 2%×候选) 视为噪声。
   - 掩码：`mask`（保留前后 N 位）、`hash`（sha256+盐 截取）、`generalize`（年龄→区间 / 邮编→前缀 /
     日期→年 / 地址→行政区前缀）、`suppress`（整值替换）。
2. **k-匿名 / ℓ-diversity + 泛化层级搜索**（`backend/src/services/k_anonymity_service.py`）
   - 等价类 = 按当前泛化层级的准标识组合分组；k = 最小组大小，ℓ = 每组敏感值最少不同值数。
   - 层级：年龄 1 岁 → 5 岁 → 10 岁区间；邮编 5 → 3 → 2 位；枚举全部组合（9 种），
     在 k≥目标、ℓ≥目标下最小化 **信息损失 = 0.5×层级损失 + 0.5×区分度损失**，返回推荐层级。
   - 年龄基准日固定为 `2026-11-10`，seed/校验可复现。
3. **异步执行**：k-匿名校验与导出文件生成由 Celery worker 执行（任务名 `maskguard.run_k_anonymity` /
   `maskguard.build_export`），backend 发起并落库；broker 不可用时同步兜底，前端轮询结果。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 18 + TypeScript + Vite + Zustand + react-router |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic + Celery |
| 数据库 | PostgreSQL 16（元数据 `meta` schema + 上游 `clinic` schema） |
| 队列 | Redis 7（Celery broker / 限流桶 / worker 心跳） |
| 网关 | Nginx 1.27（`/api/` 反代 backend + SPA 回落） |

## 目录

```
backend/
  src/{config,constants,models,schemas,services,controllers,middlewares,routes,utils,migrations}
  scripts/seed_demo.py
worker/
  src/{config,tasks}          # Celery 应用与真实任务
frontend/
  src/{api,stores,types,constants,hooks,utils,components/{common,layout},pages,router,styles}
```

## 环境变量

见 `.env.example`：`COMPOSE_PROJECT_NAME`、`FRONTEND_PORT=18224`、`BACKEND_PORT=19224`、`DB_PORT=17724`、
`DB_NAME/DB_USER/DB_PASSWORD`、`JWT_SECRET`、`HASH_SALT`、`REDIS_URL`、`ARTIFACT_DIR`、
`RATE_LIMIT_PER_MINUTE`、`SEED_DEMO`。

## 共享枚举（前后端各一份，改动必须同步）

- 后端：`backend/src/constants/enums.py`（PIIType / MaskMethod / GeneralizeKind / SensitivityLevel /
  ColumnRole / ExportStatus / BuildStatus / CheckStatus / AuditAction）
- 前端：`frontend/src/constants/enums.ts`（同名枚举 + 中文标签），角色权限矩阵：
  `backend/src/constants/roles.py` ↔ `frontend/src/constants/rbac.ts`

## 演示账号

| 邮箱 | 角色 | 口令 |
| --- | --- | --- |
| admin@clinic.local | admin | Demo@2026 |
| dpo@clinic.local | dpo | Demo@2026 |
| client@clinic.local | client | Demo@2026 |

## Seed 数据（幂等，自然键 upsert）

3 张表 / 23 列 / 6 条 PII 证据 / 5 条策略 / 3 个导出申请（待审批、已批准、已驳回）/ 1 次 k-匿名校验；
`patients` 800 行（前 60 行含 18 位身份证，58 条校验位正确、2 条故意写错）、`visits` 2400 行、`labs` 1200 行。
seed 结束时打印 `SEED_SUMMARY {json}`，连跑两次数字一致。

## License

MIT
