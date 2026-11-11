"""k-匿名校验任务：backend 创建记录后投递，worker 真算并落库。"""
from __future__ import annotations

from worker_src.config.celery_app import celery_app


@celery_app.task(name="maskguard.run_k_anonymity", bind=True)
def run_k_anonymity(self, check_id: str) -> dict:
    from src.config.database import session_scope
    from src.models.k_anonymity_check import KAnonymityCheck
    from src.services import k_anonymity_service

    with session_scope() as db:
        check = db.get(KAnonymityCheck, check_id)
        if check is None:
            return {"status": "missing", "check_id": check_id}
        if check.status == "succeeded":
            return {"status": "already_done", "check_id": check_id}
        check.status = "running"
        db.commit()
        k_anonymity_service.execute_check(db, check)
        return {
            "status": check.status,
            "check_id": check_id,
            "base_k": check.base_k,
            "final_k": check.final_k,
            "final_l": check.final_l,
            "passed": check.passed,
        }
