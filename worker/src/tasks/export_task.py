"""导出批处理任务：审批通过后由 worker 生成脱敏 CSV 并落摘要。"""
from __future__ import annotations

from worker_src.config.celery_app import celery_app


@celery_app.task(name="maskguard.build_export", bind=True)
def build_export(self, request_id: str) -> dict:
    from src.config.database import session_scope
    from src.models.export_request import ExportRequest
    from src.services import export_service

    with session_scope() as db:
        request = db.get(ExportRequest, request_id)
        if request is None:
            return {"status": "missing", "request_id": request_id}
        if request.build_status == "done":
            return {"status": "already_done", "request_id": request_id, "rows": request.masked_rows}
        result = export_service.build_export(db, request_id)
        return {"status": "done", **result}
