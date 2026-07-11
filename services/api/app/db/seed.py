from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Change, EntityState, Lab, LabChangeInterpretation, LabProfile, Source, WatchItem


GLASS_CORE_LAB_ID = "lab-glass-core"


def seed_database(db: Session) -> None:
    now = datetime.now(timezone.utc)

    watch_items = [
        WatchItem(id="topic-glass-core", kind="topic", name="Glass Core", description="玻璃基板、TGV 与先进封装载板"),
        WatchItem(id="topic-hbm", kind="topic", name="HBM", description="高带宽存储与先进封装"),
        WatchItem(id="topic-cooling", kind="topic", name="Cooling", description="AI 芯片散热与热管理"),
        WatchItem(id="company-intel", kind="company", name="Intel", description="芯片制造与 Glass Core 路线"),
        WatchItem(id="company-samsung", kind="company", name="Samsung", description="先进封装与存储路线"),
        WatchItem(id="company-absolics", kind="company", name="Absolics", description="玻璃基板产品与量产进展"),
        WatchItem(id="university-tokyo", kind="university", name="东京大学", description="材料、TGV 与封装研究"),
        WatchItem(id="university-mit", kind="university", name="MIT", description="先进封装与热管理研究"),
        WatchItem(id="conference-ectc", kind="conference", name="ECTC", description="电子元件与封装技术会议"),
        WatchItem(id="conference-iedm", kind="conference", name="IEDM", description="国际电子器件会议"),
    ]
    for item in watch_items:
        if db.get(WatchItem, item.id) is None:
            db.add(item)

    if db.get(Lab, GLASS_CORE_LAB_ID) is None:
        db.add(
            Lab(
                id=GLASS_CORE_LAB_ID,
                name="Glass Core Lab",
                description="关注玻璃基板、TGV、先进封装载板与量产可靠性的 Lab。",
            )
        )

    if db.get(LabProfile, GLASS_CORE_LAB_ID) is None:
        db.add(
            LabProfile(
                lab_id=GLASS_CORE_LAB_ID,
                research_scope={
                    "materials": ["glass core substrate", "TGV", "advanced packaging"],
                    "questions": ["量产成熟度", "可靠性验证", "供应链可得性"],
                },
                watchlist={
                    "companies": ["Intel", "Samsung", "Absolics", "日本材料与设备供应商"],
                    "signals": ["工程验证", "客户认证", "设备采购", "可靠性测试"],
                },
                key_questions=[
                    "玻璃基板是否从样品展示进入工程验证？",
                    "TGV 与翘曲控制的可靠性证据是否增强？",
                    "日本供应链是否出现可落地的材料、加工或检测节点？",
                ],
            )
        )

    sources = [
        Source(
            id="src-glass-core-engineering",
            source_type="company_signal",
            title="Glass core substrate engineering validation signal",
            url="https://example.local/glass-core-engineering",
            published_at=now,
            raw_metadata={"seed": True},
        ),
        Source(
            id="src-tgv-reliability",
            source_type="paper_signal",
            title="TGV reliability combined test signal",
            url="https://example.local/tgv-reliability",
            published_at=now,
            raw_metadata={"seed": True},
        ),
        Source(
            id="src-japan-supply-chain",
            source_type="supply_chain_signal",
            title="Japan glass core supply chain signal",
            url="https://example.local/japan-supply-chain",
            published_at=now,
            raw_metadata={"seed": True},
        ),
    ]
    for source in sources:
        if db.get(Source, source.id) is None:
            db.add(source)

    states = [
        EntityState(
            id="state-glass-core-before",
            entity_type="technology",
            entity_name="Glass Core Substrate",
            state_summary="过去主要停留在样品展示、概念验证与少量实验室可靠性数据。",
            observed_at=now,
            source_id="src-glass-core-engineering",
            raw_metadata={"seed": True},
        ),
        EntityState(
            id="state-tgv-before",
            entity_type="process",
            entity_name="Through Glass Via reliability",
            state_summary="过去公开研究更多聚焦单一指标，工程场景下的组合测试证据较少。",
            observed_at=now,
            source_id="src-tgv-reliability",
            raw_metadata={"seed": True},
        ),
        EntityState(
            id="state-supply-chain-before",
            entity_type="ecosystem",
            entity_name="Japan glass core supply chain",
            state_summary="过去供应链线索分散，材料、加工、检测之间缺少连续的落地信号。",
            observed_at=now,
            source_id="src-japan-supply-chain",
            raw_metadata={"seed": True},
        ),
    ]
    for state in states:
        if db.get(EntityState, state.id) is None:
            db.add(state)

    changes = [
        Change(
            id="chg-001",
            title="Glass Core 工程验证信号增强",
            new_facts=[
                "公开资料中出现更明确的工程验证和产线准备表述。",
                "相关岗位与设备准备信号开始从研发侧延伸到制造侧。",
            ],
            previous_state="以样品展示和实验验证为主，量产路径仍偏早期。",
            current_state="工程验证信号增强，量产路径比过去更清晰。",
            change_summary="Glass Core 从展示型信号向工程验证信号移动。",
            importance="A",
            watch_item_ids=["topic-glass-core", "company-intel", "company-absolics"],
            evidence=[
                {
                    "source_id": "src-glass-core-engineering",
                    "source_title": "Glass core substrate engineering validation signal",
                    "evidence_text": "工程验证、产线准备与制造岗位信号同时出现。",
                    "url": "https://example.local/glass-core-engineering",
                }
            ],
            next_watch_points=["客户认证进展", "良率披露", "量产线规模", "关键设备采购"],
            detected_at=now,
        ),
        Change(
            id="chg-002",
            title="TGV 可靠性研究出现新的组合测试路径",
            new_facts=[
                "最新研究将热循环、翘曲和互连失效放在同一测试框架中讨论。",
                "可靠性关注点从单点指标转向多物理场联合验证。",
            ],
            previous_state="单一可靠性指标研究较多，组合测试证据不足。",
            current_state="多物理场联合验证开始增加，工程风险画像更完整。",
            change_summary="TGV 可靠性验证正在从单点测试走向组合测试。",
            importance="B",
            watch_item_ids=["topic-glass-core", "university-tokyo", "conference-ectc"],
            evidence=[
                {
                    "source_id": "src-tgv-reliability",
                    "source_title": "TGV reliability combined test signal",
                    "evidence_text": "热循环、翘曲、互连失效被联合分析。",
                    "url": "https://example.local/tgv-reliability",
                }
            ],
            next_watch_points=["测试样本规模", "失效模式分类", "与有机载板对照数据"],
            detected_at=now,
        ),
        Change(
            id="chg-003",
            title="日本玻璃基板供应链关联度上升",
            new_facts=[
                "材料、加工和检测环节出现更连续的合作线索。",
                "本土设备与检测能力可能成为玻璃基板落地的重要支撑。",
            ],
            previous_state="供应链线索分散，难以判断是否形成闭环。",
            current_state="材料、加工、检测之间的关联度上升，区域协同迹象更明显。",
            change_summary="日本供应链从零散节点向可组合能力移动。",
            importance="B",
            watch_item_ids=["topic-glass-core", "company-samsung", "conference-ectc"],
            evidence=[
                {
                    "source_id": "src-japan-supply-chain",
                    "source_title": "Japan glass core supply chain signal",
                    "evidence_text": "材料、加工和检测线索在同一技术路径上汇合。",
                    "url": "https://example.local/japan-supply-chain",
                }
            ],
            next_watch_points=["材料供应商认证", "检测设备订单", "联合开发公告"],
            detected_at=now,
        ),
    ]
    for change in changes:
        existing_change = db.get(Change, change.id)
        if existing_change is None:
            db.add(change)
        else:
            existing_change.watch_item_ids = change.watch_item_ids

    interpretations = [
        LabChangeInterpretation(
            id="interp-001",
            lab_id=GLASS_CORE_LAB_ID,
            change_id="chg-001",
            relevance_score=0.95,
            why_relevant="这直接对应 Glass Core Lab 对量产成熟度的核心判断问题。",
            impact="可以将玻璃基板成熟度判断从“概念验证偏强”上调到“工程验证值得重点跟踪”。",
            next_watch_points=["客户认证是否出现名称级证据", "是否披露良率或产线节拍", "设备采购是否进入批量阶段"],
        ),
        LabChangeInterpretation(
            id="interp-002",
            lab_id=GLASS_CORE_LAB_ID,
            change_id="chg-002",
            relevance_score=0.88,
            why_relevant="TGV 可靠性是玻璃基板能否进入高端封装的关键技术门槛。",
            impact="Lab 对风险的判断应从“缺少可靠性证据”调整为“组合测试框架开始形成，但工程样本仍不足”。",
            next_watch_points=["热循环条件是否接近客户规格", "翘曲与互连失效是否有统一模型", "是否出现长期可靠性数据"],
        ),
        LabChangeInterpretation(
            id="interp-003",
            lab_id=GLASS_CORE_LAB_ID,
            change_id="chg-003",
            relevance_score=0.81,
            why_relevant="供应链连续性决定 Glass Core Lab 后续样品、加工和验证资源是否可获得。",
            impact="日本供应链可以作为 Glass Core Lab 的重点区域观察对象，优先跟踪材料和检测节点。",
            next_watch_points=["材料供应商是否进入客户认证", "检测能力是否覆盖 TGV 缺陷", "是否出现跨环节联合开发"],
        ),
    ]
    for interpretation in interpretations:
        if db.get(LabChangeInterpretation, interpretation.id) is None:
            db.add(interpretation)

    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_database(db)


if __name__ == "__main__":
    main()
