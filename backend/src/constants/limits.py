"""算法与接口的规模上限（防止一次请求把整库读进内存）。"""
from __future__ import annotations

# PII 扫描：每列最多读取的行数（patients 800 行全量；大表按前 N 行采样）
PII_SCAN_MAX_ROWS = 2000
# 列画像：每列样例值条数
COLUMN_SAMPLE_SIZE = 8
# PII 证据：返回的命中样例条数
PII_EVIDENCE_SAMPLES = 12
# 策略预览：每列参与预览的行数 / 返回样例条数
PREVIEW_MAX_ROWS = 800
PREVIEW_SAMPLES = 10
# k-匿名：参与计算的最大行数 / 返回的等价类条数 / 泛化候选组合上限
KANON_MAX_ROWS = 5000
KANON_MAX_CLASSES = 80
# 导出：单次导出的最大行数
EXPORT_MAX_ROWS = 5000
# 接口限流（每分钟，按用户+路径）
RATE_LIMIT_DEFAULT_PER_MINUTE = 120
RATE_LIMIT_EXPORT_PER_MINUTE = 20
