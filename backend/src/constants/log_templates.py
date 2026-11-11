"""结构化日志模板：{字段} 占位，由 utils.logger.render 填充。"""
from __future__ import annotations

LOG_TEMPLATES: dict[str, str] = {
    "auth.login": "auth.login email={email} role={role} ok={ok}",
    "pii.scan": "pii.scan table={table} column={column} type={pii_type} hit={hit} conf={confidence}",
    "pii.scan.done": "pii.scan.done table={table} columns={columns} findings={findings}",
    "policy.preview": "policy.preview policy={policy} columns={columns} rows={rows}",
    "kanon.start": "kanon.start table={table} qi={qi} k={k}",
    "kanon.done": "kanon.done check={check} base_k={base_k} rec_k={rec_k} pass={passed}",
    "kanon.failed": "kanon.failed check={check} reason={reason}",
    "export.submit": "export.submit request={request} requester={requester} table={table}",
    "export.gate": "export.gate request={request} passed={passed} gaps={gaps}",
    "export.blocked": "export.blocked request={request} gaps={gaps}",
    "export.build": "export.build request={request} rows={rows} digest={digest}",
    "export.build.skip": "export.build.skip request={request} digest={digest}",
    "export.failed": "export.failed request={request} reason={reason}",
}
