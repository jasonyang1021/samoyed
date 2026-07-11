# Dify Workflow Setup

This project calls published Dify workflows from the API server. Dify does not write to the Research Radar database; it returns structured JSON and the API persists the result.

## 1. Analyzer Workflow

Create a published Workflow application named `Research Radar Analyzer`.

Add three text inputs:

- `prompt`: the complete article and analysis instruction
- `schema_name`: the output schema name
- `schema`: the JSON schema as text

Recommended nodes:

1. Start node with the three inputs above.
2. LLM node. Pass `prompt` to the model and instruct it to return only valid JSON matching `schema`.
3. End node with one text output named `result`, mapped to the LLM response.

Use this system instruction in the LLM node:

```text
You are the senior analyst for AI Research Radar. Analyze public research information for a Glass Core Lab. Do not invent facts. Treat the supplied prompt as the source of truth. Return only valid JSON, without Markdown fences, and follow the schema included in the prompt exactly. Use concise Chinese text. Identify whether the item is materially relevant to glass substrates, glass core, TGV, advanced packaging, reliability, interconnects, HBM, or adjacent semiconductor packaging.
```

The API expects these output fields:

```json
{
  "relevance_score": 0.0,
  "is_relevant": true,
  "category": "company",
  "matched_entities": [],
  "extracted_facts": [],
  "summary": "",
  "previous_state": "",
  "current_state": "",
  "change_summary": "",
  "importance": "A",
  "lab_why_relevant": "",
  "lab_impact": ""
}
```

## 2. Search Workflow

Create a second published Workflow application named `Research Radar Search`.

Use the same three inputs and one `result` text output. Add a web search tool or search plugin in the workflow, then ask the model to return only this JSON shape:

```json
{
  "results": [
    {
      "title": "",
      "url": "https://example.com/article",
      "summary": "",
      "published_at": null,
      "source_type": "company_news",
      "authors": []
    }
  ]
}
```

The search workflow should prioritize official company newsrooms, university and lab pages, IEEE and conference pages, patent databases, arXiv, and reputable research news. Search results must include a public URL. Do not fabricate a URL or publication date.

## 3. Environment

Use the API key for the Analyzer application as `DIFY_API_KEY` and the Search application as `DIFY_SEARCH_API_KEY`:

```env
AI_PROVIDER=dify
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_API_KEY=
DIFY_SEARCH_API_KEY=
DIFY_USER=research-radar
```

Restart the API and check:

```text
GET /api/ai/status
GET /api/ai/dify/check
```

The first endpoint reports the active provider. The second verifies the Analyzer key against Dify's application parameters endpoint. The key is never returned to the browser.
