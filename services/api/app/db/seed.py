"""Production-safe database bootstrap.

The application bootstrap intentionally creates infrastructure settings only.
Demo/domain data lives in ``services/api/examples/demo_seed.py`` and must be
loaded explicitly by a developer.
"""

from app.db.database import SessionLocal
import json
from urllib.parse import quote

from app.db.models import RadarSettings, Source
from app.core.config import settings


def _generated_catalog_sources() -> list[Source]:
    """Build a broad, disabled-by-default catalog of reusable public feeds."""
    topics = [
        ("glass-core", "Glass substrate / TGV", ["glass substrate", "TGV", "glass core"]),
        ("advanced-packaging", "Advanced packaging", ["advanced packaging", "semiconductor packaging"]),
        ("cpo", "CPO / optical interconnect", ["CPO", "optical interconnect", "silicon photonics"]),
        ("hbm", "HBM / high bandwidth memory", ["HBM", "high bandwidth memory", "memory packaging"]),
        ("chiplets", "Chiplets / 2.5D / 3D integration", ["chiplet", "2.5D", "3D integration"]),
        ("pcb", "PCB / high-speed laminate", ["PCB", "signal integrity", "high-speed laminate"]),
        ("mlcc", "MLCC / passive components", ["MLCC", "ceramic capacitor", "AI server"]),
        ("thermal", "AI chip cooling / thermal management", ["thermal management", "liquid cooling", "AI chip"]),
        ("silicon-photonics", "Silicon photonics", ["silicon photonics", "optical computing"]),
        ("power", "Power semiconductors", ["power semiconductor", "SiC", "GaN"]),
        ("memory", "Memory technology", ["memory", "DRAM", "NAND"]),
        ("semiconductor-materials", "Semiconductor materials", ["semiconductor materials", "wafer", "substrate"]),
        ("reliability", "Package reliability", ["package reliability", "warpage", "reliability testing"]),
        ("manufacturing", "Semiconductor manufacturing", ["semiconductor manufacturing", "yield", "process technology"]),
        ("ai-accelerator", "AI accelerator hardware", ["AI accelerator", "GPU", "NPU"]),
        ("data-center", "Data center hardware", ["data center", "server", "rack scale"]),
        ("rf", "RF and high-frequency electronics", ["RF", "high frequency", "microwave"]),
        ("sensors", "Sensors and edge hardware", ["sensor", "edge computing", "embedded"]),
        ("quantum", "Quantum hardware", ["quantum computing", "quantum hardware"]),
        ("robotics", "Robotics hardware", ["robotics", "actuator", "machine vision"]),
        ("co-design", "Hardware / software co-design", ["hardware software co-design", "systems architecture", "AI accelerator"]),
        ("compute-in-memory", "Compute in memory", ["compute in memory", "processing in memory", "memory computing"]),
        ("neuromorphic", "Neuromorphic computing", ["neuromorphic", "spiking neural network", "event-driven computing"]),
        ("photonic-computing", "Photonic computing", ["photonic computing", "optical neural network", "photonic processor"]),
        ("optical-i-o", "Optical I/O", ["optical I/O", "optical engine", "co-packaged optics"]),
        ("interposer", "Interposer and advanced substrate", ["interposer", "silicon interposer", "package substrate"]),
        ("fan-out", "Fan-out packaging", ["fan-out packaging", "FOWLP", "FOPLP"]),
        ("hybrid-bonding", "Hybrid bonding", ["hybrid bonding", "wafer bonding", "die bonding"]),
        ("3d-stacking", "3D semiconductor stacking", ["3D stacking", "3D IC", "vertical integration"]),
        ("die-to-die", "Die-to-die interconnect", ["die-to-die", "UCIe", "chiplet interconnect"]),
        ("high-speed-io", "High-speed I/O", ["high-speed I/O", "PCIe", "CXL"]),
        ("serdes", "SerDes and signal integrity", ["SerDes", "signal integrity", "equalization"]),
        ("substrate", "Package substrate technology", ["package substrate", "ABF substrate", "BT substrate"]),
        ("ceramic-substrate", "Ceramic substrates", ["ceramic substrate", "aluminum nitride", "AlN substrate"]),
        ("glass-interposer", "Glass interposer", ["glass interposer", "glass carrier", "TGV interposer"]),
        ("wafer-level", "Wafer-level packaging", ["wafer-level packaging", "WLP", "wafer level"]),
        ("advanced-lithography", "Advanced lithography", ["EUV", "advanced lithography", "high NA"]),
        ("process-control", "Process control and metrology", ["process control", "semiconductor metrology", "inspection"]),
        ("yield-engineering", "Yield engineering", ["yield engineering", "defect inspection", "semiconductor yield"]),
        ("fab-equipment", "Semiconductor fab equipment", ["semiconductor equipment", "wafer fabrication", "fab equipment"]),
        ("chemical-mechanical", "Chemical mechanical polishing", ["chemical mechanical polishing", "CMP", "planarization"]),
        ("thin-films", "Thin films and deposition", ["thin film deposition", "ALD", "CVD"]),
        ("materials-science", "Electronic materials science", ["electronic materials", "functional materials", "materials science"]),
        ("thermal-interface", "Thermal interface materials", ["thermal interface material", "TIM", "heat spreading"]),
        ("liquid-cooling", "Liquid cooling and immersion", ["liquid cooling", "immersion cooling", "cold plate"]),
        ("power-delivery", "Power delivery networks", ["power delivery network", "PDN", "voltage regulator"]),
        ("battery", "Batteries and energy storage", ["battery technology", "energy storage", "solid state battery"]),
        ("automotive-electronics", "Automotive electronics", ["automotive electronics", "vehicle computing", "ADAS hardware"]),
        ("edge-ai", "Edge AI hardware", ["edge AI", "embedded AI", "on-device AI"]),
        ("security-hardware", "Hardware security", ["hardware security", "trusted execution", "secure processor"]),
    ]
    sources: list[Source] = []
    for slug, label, tags in topics:
        query = quote(" OR ".join(tags))
        encoded_label = quote(label)
        patent_query = quote(json.dumps({"_text_any": {"patent_title": " ".join(tags)}}, separators=(",", ":")))
        sources.extend([
            Source(id=f"catalog-arxiv-{slug}", source_type="paper_feed", title=f"arXiv · {label}", url=f"https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending", enabled=False, raw_metadata={"format": "arxiv", "catalog": True, "recommendation_tags": tags}),
            Source(id=f"catalog-openalex-{slug}", source_type="paper_api", title=f"OpenAlex · {label}", url=f"https://api.openalex.org/works?search={query}&per-page=50", enabled=False, raw_metadata={"format": "openalex", "catalog": True, "recommendation_tags": tags}),
            Source(id=f"catalog-crossref-{slug}", source_type="paper_api", title=f"Crossref · {label}", url=f"https://api.crossref.org/works?query.title={encoded_label}&rows=50&select=DOI,title,abstract,author,published", enabled=False, raw_metadata={"format": "crossref", "catalog": True, "recommendation_tags": tags}),
            Source(id=f"catalog-semantic-scholar-{slug}", source_type="paper_api", title=f"Semantic Scholar · {label}", url=f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=50&fields=title,abstract,authors,publicationDate,url", enabled=False, raw_metadata={"format": "semantic_scholar", "catalog": True, "recommendation_tags": tags}),
            Source(id=f"catalog-openalex-conference-{slug}", source_type="conference_article", title=f"OpenAlex · {label} conference papers", url=f"https://api.openalex.org/works?search={query}&filter=type:proceedings-article&per-page=50", enabled=False, raw_metadata={"format": "openalex", "catalog": True, "recommendation_tags": [*tags, "conference"]}),
            Source(id=f"catalog-crossref-conference-{slug}", source_type="conference_article", title=f"Crossref · {label} conference proceedings", url=f"https://api.crossref.org/works?query={encoded_label}&filter=type:proceedings-article&rows=50&select=DOI,title,abstract,author,published,container-title", enabled=False, raw_metadata={"format": "crossref", "catalog": True, "recommendation_tags": [*tags, "conference"]}),
            Source(id=f"catalog-news-{slug}", source_type="news_feed", title=f"Google News · {label}", url=f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US%3Aen", enabled=False, raw_metadata={"format": "rss", "catalog": True, "recommendation_tags": tags}),
            Source(id=f"catalog-europe-pmc-{slug}", source_type="paper_api", title=f"Europe PMC · {label}", url=f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize=100&resultType=core", enabled=False, raw_metadata={"format": "europe_pmc", "catalog": True, "recommendation_tags": tags}),
            Source(id=f"catalog-patents-{slug}", source_type="patent_api", title=f"Google Patents · {label}", url=f"https://patents.google.com/xhr/query?url=q%3D{query}&exp=", enabled=False, raw_metadata={"format": "google_patents", "catalog": True, "recommendation_tags": [*tags, "patent"]}),
            Source(id=f"catalog-patentsview-{slug}", source_type="patent_api", title=f"PatentsView · {label}", url=f"https://search.patentsview.org/api/v1/patent/?q={patent_query}&f=%5B%22patent_id%22,%22patent_title%22,%22patent_date%22,%22patent_abstract%22%5D&o=%7B%22size%22:100%7D", enabled=False, raw_metadata={"format": "patentsview", "catalog": True, "requires_api_key": True, "recommendation_tags": [*tags, "patent"]}),
        ])
    for source in sources:
        metadata = dict(source.raw_metadata or {})
        metadata.setdefault("max_pages", 2)
        metadata.setdefault("page_size", 50)
        source.raw_metadata = metadata
    return sources


def seed_database(db) -> None:
    if db.get(RadarSettings, "default") is None:
        db.add(RadarSettings(id="default", enabled=False, run_time="08:00", timezone="Asia/Tokyo"))
    default_sources = [
        Source(
            id="src-default-arxiv-ai-hardware",
            source_type="paper_feed",
            title="arXiv · AI hardware and advanced packaging",
            url="https://export.arxiv.org/api/query?search_query=all:%22advanced%20packaging%22%20OR%20all:HBM%20OR%20all:CPO&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending",
            raw_metadata={"format": "arxiv", "default": True, "recommendation_tags": ["advanced packaging", "HBM", "CPO", "AI hardware"]},
        ),
        Source(
            id="src-default-openalex-research",
            source_type="paper_api",
            title="OpenAlex · Semiconductor and packaging research",
            url="https://api.openalex.org/works?search=semiconductor%20advanced%20packaging%20HBM%20CPO&per-page=50",
            raw_metadata={"format": "openalex", "default": True, "recommendation_tags": ["semiconductor", "advanced packaging", "HBM", "CPO"]},
        ),
        Source(
            id="src-default-google-news-ai-hardware",
            source_type="news_feed",
            title="Google News · AI hardware and semiconductor news",
            url="https://news.google.com/rss/search?q=%28AI%20chip%20OR%20semiconductor%20OR%20advanced%20packaging%20OR%20HBM%29&hl=en-US&gl=US&ceid=US%3Aen",
            raw_metadata={"format": "rss", "default": True, "recommendation_tags": ["AI", "semiconductor", "HBM", "packaging"]},
        ),
        Source(
            id="src-default-intel-newsroom",
            source_type="company_news",
            title="Intel Newsroom",
            url="https://newsroom.intel.com/",
            raw_metadata={"format": "html", "default": True, "recommendation_tags": ["Intel", "semiconductor", "advanced packaging"]},
        ),
        Source(
            id="src-default-europe-pmc",
            source_type="paper_api",
            title="Europe PMC · Engineering and materials research",
            url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%28semiconductor%20OR%20advanced%20packaging%20OR%20materials%29&format=json&pageSize=100&resultType=core",
            raw_metadata={"format": "europe_pmc", "default": True, "recommendation_tags": ["materials", "semiconductor", "packaging"]},
        ),
        Source(id="src-arxiv-glass-core", source_type="paper_feed", title="arXiv · Glass Core research", url="https://export.arxiv.org/api/query?search_query=all:%22glass%20substrate%22%20OR%20all:%22glass%20core%22%20OR%20all:%22through%20glass%20via%22&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending", raw_metadata={"format": "arxiv", "default": True, "recommendation_tags": ["glass substrate", "glass core", "TGV"]}),
        Source(id="src-crossref-glass-core", source_type="paper_api", title="Crossref · Glass Core research", url="https://api.crossref.org/works?query.title=glass%20substrate&rows=50&select=DOI,title,abstract,author,published", raw_metadata={"format": "crossref", "default": True, "recommendation_tags": ["glass substrate", "advanced packaging"]}),
        Source(id="src-openalex-glass-packaging", source_type="paper_api", title="OpenAlex · Glass substrate and TGV research", url="https://api.openalex.org/works?search=glass%20substrate%20TGV%20advanced%20packaging&per-page=50", raw_metadata={"format": "openalex", "default": True, "recommendation_tags": ["glass substrate", "TGV", "advanced packaging"]}),
        Source(id="src-semantic-scholar-glass-packaging", source_type="paper_api", title="Semantic Scholar · Glass substrate / TGV research", url="https://api.semanticscholar.org/graph/v1/paper/search?query=glass%20substrate%20TGV%20advanced%20packaging&limit=100&fields=title,abstract,authors,publicationDate,url", raw_metadata={"format": "semantic_scholar", "default": True, "recommendation_tags": ["glass substrate", "TGV", "advanced packaging"]}),
        Source(id="src-europe-pmc-packaging", source_type="paper_api", title="Europe PMC · Semiconductor packaging research", url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%28%22glass%20substrate%22%20OR%20TGV%20OR%20%22advanced%20packaging%22%29&format=json&pageSize=100&resultType=core", raw_metadata={"format": "europe_pmc", "default": True, "recommendation_tags": ["glass substrate", "TGV", "advanced packaging"]}),
        Source(id="src-google-news-glass", source_type="news_feed", title="Google News · Glass substrate", url="https://news.google.com/rss/search?q=%28%22glass%20substrate%22%20OR%20%22glass%20core%22%20OR%20TGV%29&hl=en-US&gl=US&ceid=US%3Aen", raw_metadata={"format": "rss", "default": True, "recommendation_tags": ["glass substrate", "glass core", "TGV"]}),
        Source(id="src-intel-glass-substrate", source_type="company_news", title="Intel Newsroom · Glass Substrates", url="https://newsroom.intel.com/artificial-intelligence/intel-unveils-industry-leading-glass-substrates", raw_metadata={"format": "html", "default": True, "recommendation_tags": ["Intel", "glass substrate"]}),
        Source(id="src-samsung-glass-core", source_type="company_news", title="Samsung Electro-Mechanics · Glass Core", url="https://www.samsungsem.com/global/newsroom/news/view.do?id=9622", raw_metadata={"format": "html", "default": True, "recommendation_tags": ["Samsung", "glass core"]}),
        Source(id="src-neg-glass-core", source_type="company_product", title="Nippon Electric Glass · Inorganic Core Substrate", url="https://www.neg.co.jp/en/products/inorganic-core-substrate/index.html", raw_metadata={"format": "html", "default": True, "recommendation_tags": ["glass substrate", "Japan", "core substrate"]}),
        Source(id="src-imaps-glass-substrate", source_type="conference_article", title="IMAPS · Glass Substrates for Advanced Packaging", url="https://imapsource.org/article/56156-glass-substrates-for-advanced-packaging", raw_metadata={"format": "html", "default": True, "recommendation_tags": ["glass substrate", "advanced packaging", "conference"]}),
        Source(id="src-arxiv-cpo-optical-interconnect", source_type="paper_feed", title="arXiv · CPO / Optical Interconnect research", url="https://export.arxiv.org/api/query?search_query=all:%22co-packaged%20optics%22%20OR%20all:%22optical%20interconnect%22%20OR%20all:%22silicon%20photonics%22&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending", raw_metadata={"format": "arxiv", "default": True, "recommendation_tags": ["CPO", "optical interconnect", "silicon photonics"]}),
        Source(id="src-arxiv-hbm-packaging", source_type="paper_feed", title="arXiv · HBM / memory packaging research", url="https://export.arxiv.org/api/query?search_query=all:%22high%20bandwidth%20memory%22%20OR%20all:HBM%20OR%20all:%22memory%20packaging%22&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending", raw_metadata={"format": "arxiv", "default": True, "recommendation_tags": ["HBM", "memory packaging"]}),
        Source(id="src-google-news-cpo", source_type="news_feed", title="Google News · CPO / optical interconnect", url="https://news.google.com/rss/search?q=%28%22co-packaged%20optics%22%20OR%20CPO%20OR%20%22optical%20interconnect%22%29&hl=en-US&gl=US&ceid=US%3Aen", raw_metadata={"format": "rss", "default": True, "recommendation_tags": ["CPO", "optical interconnect"]}),
        Source(id="src-google-news-pcb", source_type="news_feed", title="Google News · PCB / high-speed laminate", url="https://news.google.com/rss/search?q=%28PCB%20OR%20%22printed%20circuit%20board%22%20OR%20%22high-speed%20laminate%22%29&hl=en-US&gl=US&ceid=US%3Aen", raw_metadata={"format": "rss", "default": True, "recommendation_tags": ["PCB", "signal integrity", "laminate"]}),
        Source(id="src-google-news-mlcc", source_type="news_feed", title="Google News · MLCC / AI server passives", url="https://news.google.com/rss/search?q=%28MLCC%20OR%20%22multilayer%20ceramic%20capacitor%22%29%20%28AI%20OR%20server%20OR%20semiconductor%29&hl=en-US&gl=US&ceid=US%3Aen", raw_metadata={"format": "rss", "default": True, "recommendation_tags": ["MLCC", "AI server", "ceramic capacitor"]}),
        Source(id="src-google-news-hbm", source_type="news_feed", title="Google News · HBM / advanced memory", url="https://news.google.com/rss/search?q=%28HBM%20OR%20%22high%20bandwidth%20memory%22%20OR%20HBM4%29&hl=en-US&gl=US&ceid=US%3Aen", raw_metadata={"format": "rss", "default": True, "recommendation_tags": ["HBM", "memory", "advanced packaging"]}),
        Source(id="src-google-patents-glass", source_type="patent_api", title="Google Patents · Glass substrate / TGV", url="https://patents.google.com/xhr/query?url=q%3Dglass%2Bsubstrate&exp=", raw_metadata={"format": "google_patents", "default": True, "recommendation_tags": ["patent", "glass substrate", "TGV"]}),
        Source(id="src-patentsview-glass", source_type="patent_api", title="PatentsView · Glass substrate / TGV patents", url="https://search.patentsview.org/api/v1/patent/", raw_metadata={"format": "patentsview", "default": True, "recommendation_tags": ["patent", "glass substrate", "TGV"]}),
    ]
    default_sources.extend(_generated_catalog_sources())
    core_source_ids: set[str] = set()
    for source in default_sources:
        if source.id not in core_source_ids:
            source.enabled = False
        if db.get(Source, source.id) is None:
            db.add(source)
        else:
            existing_source = db.get(Source, source.id)
            if (source.raw_metadata or {}).get("catalog"):
                existing_source.title = source.title
                existing_source.url = source.url
                existing_source.source_type = source.source_type
                existing_source.raw_metadata = source.raw_metadata
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_database(db)
        if settings.seed_demo_data:
            from examples.demo_seed import seed_database as seed_demo_database

            seed_demo_database(db)


if __name__ == "__main__":
    main()
