from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Change, EntityState, Lab, LabChangeInterpretation, LabProfile, LabWatchItem, RadarSettings, Source, WatchItem


GLASS_CORE_LAB_ID = "lab-glass-core"

LAB_DEFINITIONS = [
    ("lab-cpo", "CPO Lab", "关注共封装光学、光电互连和高速信号协同，追踪带宽、封装与系统集成的变化。"),
    ("lab-glass-core", "Glass Core Lab", "关注玻璃基板、TGV、先进封装载板与量产可靠性，判断技术从样品走向工程验证的进展。"),
    ("lab-pcb", "PCB Lab", "关注高速高频 PCB 材料、叠层设计与信号完整性，连接材料变化和整机性能约束。"),
    ("lab-cc", "CC Lab", "关注计算、连接与散热的系统协同，识别 AI 硬件从器件到平台的关键变化。"),
    ("lab-fujii", "Fujii Lab", "关注先进封装材料、工艺可靠性与学术研究转化，持续追踪可验证的技术路径。"),
]


def seed_database(db: Session) -> None:
    now = datetime.now(timezone.utc)

    if db.get(RadarSettings, "default") is None:
        db.add(RadarSettings(id="default", enabled=False, run_time="08:00", timezone="Asia/Tokyo"))

    watch_items = [
        WatchItem(id="topic-glass-core", kind="topic", name="Glass Core", description="玻璃基板、TGV 与先进封装载板"),
        WatchItem(id="topic-cpo", kind="topic", name="CPO", description="共封装光学、光电互连与高速带宽"),
        WatchItem(id="topic-pcb", kind="topic", name="PCB", description="高速高频 PCB、材料与信号完整性"),
        WatchItem(id="topic-cc", kind="topic", name="Compute & Connectivity", description="计算、连接、带宽与系统散热"),
        WatchItem(id="topic-hbm", kind="topic", name="HBM", description="高带宽存储与先进封装"),
        WatchItem(id="topic-mlcc", kind="topic", name="MLCC", description="AI 服务器与高端硬件用多层陶瓷电容"),
        WatchItem(id="topic-cooling", kind="topic", name="Cooling", description="AI 芯片散热与热管理"),
        WatchItem(id="company-intel", kind="company", name="Intel", description="芯片制造与 Glass Core 路线"),
        WatchItem(id="company-micron", kind="company", name="Micron", description="HBM、存储封装与先进封装路线"),
        WatchItem(id="company-tsmc", kind="company", name="TSMC", description="先进制程、封装和 CoWoS/玻璃基板路线"),
        WatchItem(id="company-nvidia", kind="company", name="NVIDIA", description="AI 加速器、HBM、CPO 与系统封装需求"),
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

    for lab_id, name, description in LAB_DEFINITIONS:
        existing_lab = db.get(Lab, lab_id)
        if existing_lab is None:
            db.add(Lab(id=lab_id, name=name, description=description))
        else:
            existing_lab.name = name
            existing_lab.description = description

    lab_watch_items = {
        "lab-cpo": ["topic-cpo", "company-intel", "conference-ectc"],
        "lab-glass-core": ["topic-glass-core", "company-intel", "company-samsung", "company-absolics", "conference-ectc"],
        "lab-pcb": ["topic-pcb", "topic-mlcc", "company-intel", "conference-ectc"],
        "lab-cc": ["topic-cc", "topic-hbm", "topic-mlcc", "topic-cooling"],
        "lab-fujii": ["topic-glass-core", "university-tokyo", "university-mit"],
    }
    for lab_id, item_ids in lab_watch_items.items():
        for item_id in item_ids:
            if db.get(LabWatchItem, {"lab_id": lab_id, "watch_item_id": item_id}) is None:
                db.add(LabWatchItem(lab_id=lab_id, watch_item_id=item_id))

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
                signal_rules={"keywords": ["glass", "tgv", "through glass via", "glass core", "substrate", "warpage"]},
                ai_policy={"require_citations": True, "minimum_confidence": 0.55},
            )
        )

    sources = [
        Source(
            id="src-arxiv-glass-core",
            source_type="paper_feed",
            title="arXiv · Glass Core research",
            url="https://export.arxiv.org/api/query?search_query=all:%22glass%20substrate%22%20OR%20all:%22glass%20core%22%20OR%20all:%22through%20glass%20via%22&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending",
            published_at=now,
            raw_metadata={"seed": True, "format": "arxiv"},
        ),
        Source(
            id="src-crossref-glass-core",
            source_type="paper_api",
            title="Crossref · Glass Core research",
            url="https://api.crossref.org/works?query.title=glass%20substrate&filter=from-pub-date:2026-01-01,until-pub-date:2026-12-31&rows=50&select=DOI,title,abstract,author,published",
            published_at=now,
            raw_metadata={"seed": True, "format": "crossref"},
        ),
        Source(
            id="src-openalex-glass-packaging",
            source_type="paper_api",
            title="OpenAlex · Glass substrate and TGV research",
            url="https://api.openalex.org/works?search=glass%20substrate%20TGV%20advanced%20packaging&filter=from_publication_date:2026-01-01,to_publication_date:2026-12-31&per-page=50",
            published_at=now,
            raw_metadata={"seed": True, "format": "openalex"},
        ),
        Source(
            id="src-semantic-scholar-glass-packaging",
            source_type="paper_api",
            title="Semantic Scholar · Glass substrate / TGV research",
            url="https://api.semanticscholar.org/graph/v1/paper/search?query=glass%20substrate%20TGV%20advanced%20packaging&limit=100&fields=title,abstract,authors,publicationDate,url",
            published_at=now,
            raw_metadata={"seed": True, "format": "semantic_scholar"},
        ),
        Source(
            id="src-europe-pmc-packaging",
            source_type="paper_api",
            title="Europe PMC · Semiconductor packaging research",
            url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%28%22glass%20substrate%22%20OR%20TGV%20OR%20%22advanced%20packaging%22%29%20AND%20FIRST_PDATE:%5B2026-01-01%20TO%202026-12-31%5D&format=json&pageSize=100&resultType=core",
            published_at=now,
            raw_metadata={"seed": True, "format": "europe_pmc"},
        ),
        Source(
            id="src-google-news-glass",
            source_type="news_feed",
            title="Google News · Glass substrate 2026",
            url="https://news.google.com/rss/search?q=%28%22glass%20substrate%22%20OR%20%22glass%20core%22%20OR%20TGV%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-intel-glass-substrate",
            source_type="company_news",
            title="Intel Newsroom · Glass Substrates",
            url="https://newsroom.intel.com/artificial-intelligence/intel-unveils-industry-leading-glass-substrates",
            published_at=now,
            raw_metadata={"seed": True, "format": "html"},
        ),
        Source(
            id="src-samsung-glass-core",
            source_type="company_news",
            title="Samsung Electro-Mechanics · Glass Core",
            url="https://www.samsungsem.com/global/newsroom/news/view.do?id=9622",
            published_at=now,
            raw_metadata={"seed": True, "format": "html"},
        ),
        Source(
            id="src-neg-glass-core",
            source_type="company_product",
            title="Nippon Electric Glass · Inorganic Core Substrate",
            url="https://www.neg.co.jp/en/products/inorganic-core-substrate/index.html",
            published_at=now,
            raw_metadata={"seed": True, "format": "html"},
        ),
        Source(
            id="src-imaps-glass-substrate",
            source_type="conference_article",
            title="IMAPS · Glass Substrates for Advanced Packaging",
            url="https://imapsource.org/article/56156-glass-substrates-for-advanced-packaging",
            published_at=now,
            raw_metadata={"seed": True, "format": "html"},
        ),
        Source(
            id="src-google-news-semiconductor-companies",
            source_type="company_news",
            title="Google News · Micron / TSMC / NVIDIA · 2026",
            url="https://news.google.com/rss/search?q=%28Micron%20OR%20TSMC%20OR%20NVIDIA%29%20%28%22advanced%20packaging%22%20OR%20HBM%20OR%20CPO%20OR%20%22glass%20substrate%22%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-arxiv-cpo-optical-interconnect",
            source_type="paper_feed",
            title="arXiv · CPO / Optical Interconnect research",
            url="https://export.arxiv.org/api/query?search_query=all:%22co-packaged%20optics%22%20OR%20all:%22optical%20interconnect%22%20OR%20all:%22silicon%20photonics%22&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending",
            published_at=now,
            raw_metadata={"seed": True, "format": "arxiv"},
        ),
        Source(
            id="src-arxiv-hbm-packaging",
            source_type="paper_feed",
            title="arXiv · HBM / memory packaging research",
            url="https://export.arxiv.org/api/query?search_query=all:%22high%20bandwidth%20memory%22%20OR%20all:HBM%20OR%20all:%22memory%20packaging%22&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending",
            published_at=now,
            raw_metadata={"seed": True, "format": "arxiv"},
        ),
        Source(
            id="src-google-news-cpo",
            source_type="news_feed",
            title="Google News · CPO / optical interconnect · 2026",
            url="https://news.google.com/rss/search?q=%28%22co-packaged%20optics%22%20OR%20CPO%20OR%20%22optical%20interconnect%22%20OR%20%22silicon%20photonics%22%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-google-news-pcb",
            source_type="news_feed",
            title="Google News · PCB / high-speed laminate · 2026",
            url="https://news.google.com/rss/search?q=%28PCB%20OR%20%22printed%20circuit%20board%22%20OR%20%22high-speed%20laminate%22%20OR%20%22package%20substrate%22%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-google-news-mlcc",
            source_type="news_feed",
            title="Google News · MLCC / AI server passives · 2026",
            url="https://news.google.com/rss/search?q=%28MLCC%20OR%20%22multilayer%20ceramic%20capacitor%22%20OR%20%22ceramic%20capacitor%22%29%20%28AI%20OR%20server%20OR%20semiconductor%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-google-news-hbm",
            source_type="news_feed",
            title="Google News · HBM / advanced memory · 2026",
            url="https://news.google.com/rss/search?q=%28HBM%20OR%20%22high%20bandwidth%20memory%22%20OR%20HBM4%20OR%20HBM3E%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-google-news-patents",
            source_type="patent_feed",
            title="Google News · Glass substrate patents · 2026",
            url="https://news.google.com/rss/search?q=%28%22glass%20substrate%22%20OR%20TGV%20OR%20%22glass%20core%22%29%20%28patent%20OR%20patents%29%20after%3A2025-12-31%20before%3A2027-01-01&hl=en-US&gl=US&ceid=US%3Aen",
            published_at=now,
            raw_metadata={"seed": True, "format": "rss"},
        ),
        Source(
            id="src-google-patents-glass",
            source_type="patent_api",
            title="Google Patents · Glass substrate / TGV · 2026",
            url="https://patents.google.com/xhr/query?url=q%3Dglass%2Bsubstrate%26after%3Dpublication%3A20260101%26before%3Dpublication%3A20261231&exp=",
            published_at=now,
            raw_metadata={"seed": True, "format": "google_patents"},
        ),
        Source(
            id="src-patentsview-glass",
            source_type="patent_api",
            title="PatentsView · Glass substrate / TGV patents",
            url="https://search.patentsview.org/api/v1/patent/?q=%7B%22_and%22:%5B%7B%22_text_any%22:%7B%22patent_title%22:%22glass%20substrate%20TGV%22%7D%7D,%7B%22_gte%22:%7B%22patent_date%22:%222026-01-01%22%7D%7D,%7B%22_lte%22:%7B%22patent_date%22:%222026-12-31%22%7D%7D%5D%7D&f=%5B%22patent_id%22,%22patent_title%22,%22patent_date%22%5D&o=%7B%22size%22:100%7D",
            published_at=now,
            raw_metadata={"seed": True, "format": "patentsview"},
        ),
    ]
    for source in sources:
        existing_source = db.get(Source, source.id)
        if existing_source is None:
            db.add(source)
        elif source.id in {"src-arxiv-glass-core", "src-crossref-glass-core"}:
            existing_source.url = source.url
            existing_source.raw_metadata = source.raw_metadata
        elif source.id in {"src-openalex-glass-packaging", "src-google-news-glass", "src-patentsview-glass"}:
            existing_source.url = source.url
            existing_source.raw_metadata = source.raw_metadata
        elif source.id.startswith(("src-arxiv-cpo", "src-arxiv-hbm", "src-google-news-cpo", "src-google-news-pcb", "src-google-news-mlcc", "src-google-news-hbm")):
            existing_source.url = source.url
            existing_source.raw_metadata = source.raw_metadata

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
