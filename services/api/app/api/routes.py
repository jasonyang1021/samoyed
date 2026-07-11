from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.change import ChangeCard

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/version")
def version() -> dict[str, str]:
    return {"name": "research-radar-api", "version": "0.1.0"}


@router.get("/api/changes/today", response_model=list[ChangeCard])
def today_changes() -> list[ChangeCard]:
    return [
        ChangeCard(
            id="chg-001",
            title="Glass Core 工程验证信号增强",
            change_summary="公开信息中出现更明确的工程验证与产线准备信号。",
            previous_state="以样品展示和实验验证为主。",
            current_state="工程验证信号增强，量产路径更清晰。",
            importance="A",
            affected_labs=["Glass Core Lab", "Advanced Packaging Lab"],
            evidence_count=3,
            published_at=datetime.now(timezone.utc),
        ),
        ChangeCard(
            id="chg-002",
            title="TGV 可靠性研究出现新的测试组合",
            change_summary="最新论文将热循环、翘曲和互连失效联合分析。",
            previous_state="单一可靠性指标研究较多。",
            current_state="多物理场联合验证开始增加。",
            importance="B",
            affected_labs=["Glass Core Lab", "Reliability Lab"],
            evidence_count=2,
            published_at=datetime.now(timezone.utc),
        ),
    ]
