# Ontology 101

Companion notebooks for a five-part series on ontologies. The series starts with the W3C stack and ends at Databricks Genie Ontology. OntoBricks (a databrickslabs project) is the bridge article. It runs the classic OWL and RDF stack on the lakehouse, one step before Genie.

All five parts use the same B2B SaaS dataset. The domain covers accounts, subscriptions, MRR, users, usage events, support tickets, and churn flags. You build the same example in rdflib, Neo4j, GraphRAG, Unity Catalog Metrics, OntoBricks, and a Genie space.

As of August 2026, Genie Ontology is in Preview (announced at DAIS 2026 on June 16). Pages are part of Unity Catalog semantics. They are the human-modeled layer of the Genie Ontology. Genie One and Genie Agents are free for user usage through January 31, 2027.

Cadence is one article every 10 days, about 8 weeks in total. Each article is 15 to 18 minutes. About 40 percent is concept and 60 percent is hands-on. Each part ends with a working artifact.

This repo holds the notebooks and the artifacts they produce. The Medium articles and the diagrams are not in this repo.

## Series index

Medium links are placeholders until each article is published.

| Part | Title | Read time | Notebook | Article |
| --- | --- | --- | --- | --- |
| 1 | What an ontology is, and the stack that formalized it | 16 min | [part-1-notebook.ipynb](ontology-101-part-1/part-1-notebook.ipynb) | [placeholder](https://medium.com/@TODO/ontology-101-part-1) |
| 2 | Knowledge graphs and GraphRAG | 17 min | Coming soon | [placeholder](https://medium.com/@TODO/ontology-101-part-2) |
| 3 | Semantic layers | 15 min | Coming soon | [placeholder](https://medium.com/@TODO/ontology-101-part-3) |
| 4 | OntoBricks: the W3C stack on the lakehouse | 18 min | Coming soon | [placeholder](https://medium.com/@TODO/ontology-101-part-4) |
| 5 | Genie Ontology, the capstone | 18 min | Coming soon | [placeholder](https://medium.com/@TODO/ontology-101-part-5) |

## Why this series

Language models write fluent text-to-SQL, but they produce confident wrong numbers when they infer meaning from column names. The fix is a governed layer of meaning between the question and the query.

Databricks' internal 28-question suite (June 2026) showed Genie answering 84.5 percent correctly on first attempt versus 52.4 percent for the strongest general-purpose coding agent. dbt's independent paired benchmark showed a modeled semantic layer moving GPT-5.3 Codex from 84.1 to 100 percent. Both are vendor-run and specific to those benchmarks. Treat them with that caveat.

The claim of the series is that ontology is an old answer to a current problem. The same idea shows up from Aristotle's categories through Gruber's 1993 definition ("an explicit specification of a conceptualization"), the Semantic Web, knowledge graphs, semantic layers, and continuously learned context layers.

## The five articles

### Part 1. What an ontology is, and the stack that formalized it

- Article: [placeholder](https://medium.com/@TODO/ontology-101-part-1)
- Notebook: [ontology-101-part-1/part-1-notebook.ipynb](ontology-101-part-1/part-1-notebook.ipynb)
- Artifact: [ontology-101-part-1/saas_ontology.ttl](ontology-101-part-1/saas_ontology.ttl)

Concept (40 percent): Aristotle and categories, the 17th-century coinage, Gruber's computer-science definition, semantic networks and frames and description logics in brief, then the Semantic Web stack. That stack is RDF triples, RDFS, OWL, SPARQL, and Berners-Lee's 2001 vision. The article also covers why the word confuses people.

Hands-on (60 percent): model the SaaS domain first on paper (a concept map, then triples), then build a small OWL ontology in Protégé and rdflib. Query it with SPARQL. The artifact is a `.ttl` file you keep for Parts 4 and 5.

The notebook runs anywhere Python runs, including a Databricks notebook. Part 1 does not use Databricks features. SPARQL here matches what you asserted. It does not run OWL. Load the saved file into Protégé to see the reasoner classify Initech as Churned.

### Part 2. Knowledge graphs and GraphRAG

- Article: [placeholder](https://medium.com/@TODO/ontology-101-part-2)
- Notebook: coming soon

Concept: why the global Semantic Web stalled (OWL cost, n-ary awkwardness, sparse markup, intractable web-scale reasoning) and what survived (triples, IRIs, SPARQL). Google 2012 "things, not strings," schema.org, Wikidata, property graphs versus RDF. Then GraphRAG: baseline RAG limits, entity graphs, Leiden community detection, provenance.

Hands-on: load the SaaS domain into Neo4j (NetworkX fallback), write Cypher, then build Microsoft GraphRAG over a small synthetic ticket and doc corpus and compare against a vector-only baseline.

### Part 3. Semantic layers

- Article: [placeholder](https://medium.com/@TODO/ontology-101-part-3)
- Notebook: coming soon

Concept: the text-to-SQL failure mode, and why semantic-layer failures are refusals while text-to-SQL failures are confident wrong numbers. The tools in this space include dbt Semantic Layer on MetricFlow, Cube, AtScale, LookML, warehouse-native Snowflake Semantic Views, and Databricks Metric Views.

Hands-on: define MRR, churn, and active user as governed metrics, first in MetricFlow, then as Unity Catalog Metric Views. This is the first landing on Databricks. The notebook shows a text-to-SQL error the layer prevents. Unity Catalog Metrics feed Genie Ontology directly, so this artifact persists.

### Part 4. OntoBricks: the W3C stack on the lakehouse

- Article: [placeholder](https://medium.com/@TODO/ontology-101-part-4)
- Notebook: coming soon

Concept: the convergence story. Everything from Parts 1 and 2 (OWL, R2RML, triple stores, reasoning) now runs natively on Databricks without separate graph infrastructure. OntoBricks is a databrickslabs project (AS-IS, no SLA). It covers visual ontology design, R2RML mapping to Unity Catalog tables, a Delta-backed triple store plus a Lakebase Postgres graph engine, OWL 2 RL / SWRL / SHACL reasoning, an auto-generated GraphQL API, and an MCP server you can use from the Databricks Playground, Cursor, or Claude Desktop. It can import industry standards (FIBO, CDISC, IOF).

Hands-on: import the Part 1 `.ttl` ontology (or rebuild it visually), auto-map to the SaaS tables in Unity Catalog via the 4-click pipeline, materialize the triple store, run a reasoning check, run the built-in pitfall scanner (19 structural, logical, and semantic checks), then query the graph from an MCP client. This needs Lakebase (v0.4.0+).

### Part 5. Genie Ontology, the capstone

- Article: [placeholder](https://medium.com/@TODO/ontology-101-part-5)
- Notebook: coming soon

Concept: authored versus learned. OntoBricks is the ontology you write. Genie Ontology is the ontology the platform learns. It extracts knowledge from tables, queries, dashboards, pipelines, and 50+ connected apps, ranked by OntoRank (a PageRank-style authority mechanism that weighs source, author authority, usage, certified-asset ties, and freshness). Pages are the human-modeled layer in Unity Catalog semantics. The article includes a short Palantir Foundry comparison (object, link, and action types as the commercial precedent) and a compressed industry sidebar (SNOMED CT, FIBO, TM Forum SID, IEC CIM). Preview-status caveat.

Hands-on: build a Genie space on the SaaS dataset, author Pages and Unity Catalog Metric definitions, plant two conflicting churn definitions, watch OntoRank resolve them, evaluate with Genie Benchmarks (up to 500 questions, chat and agent mode) and MLflow scorers, then consume via MCP at `/api/2.0/mcp/genie/{genie_space_id}` from a LangGraph agent. Note the free-usage window through January 31, 2027. Close with a decision guide: when to author (OntoBricks, Unity Catalog Metrics, Pages) versus when to let the platform learn (Genie Ontology), and the smallest governed layer that removes the most ambiguity.

## Running dataset

B2B SaaS subscription and churn data (a Kaggle SaaS churn dataset works: Customer ID, Company, Country, Plan, Billing Cycle, MRR, Monthly Active Users, Churn Flag, Churn Reason) plus a synthetic usage-event log and a small ticket and doc corpus for GraphRAG. Databricks Free Edition covers the Databricks parts. The Genie free-usage promo covers Part 5.

## How to run Part 1

The first notebook cell installs `rdflib`. You can run it locally or in a Databricks notebook.

```bash
git clone https://github.com/Praneeth16/ontology-series.git
cd ontology-series
python3 -m venv .venv
source .venv/bin/activate
pip install jupyter rdflib
jupyter notebook ontology-101-part-1/part-1-notebook.ipynb
```

## How to run Part 2

The lab is plain Python 3.11 or newer. It needs no API key, database server, or language model.

```bash
git clone https://github.com/Praneeth16/ontology-series.git
cd ontology-series/ontology-101-part-2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python lab.py
python test_lab.py
```

Open `part-2-notebook.ipynb` in Jupyter for the same walkthrough with explanations.

## Publishing notes

Each article is 15 to 18 minutes. That is longer than Medium's measured 7-minute engagement peak (Sall, Medium Data Lab). The extra length is for concept-plus-lab readers. Treat 7 minutes as an essay floor, not a lab cap.

Cadence is one article every 10 days, same day and time. About 8 weeks in total.

Retention comes from recap-and-cliffhanger bookends, the persistent dataset and artifacts (the `.ttl` file from Part 1 loads into Part 4), a visible series index, and diagrams every few hundred words.

A healthy Medium read ratio is 20 to 50 percent. Expect the lower end for these lengths. If Parts 1 or 2 fall below 20 percent, split the remaining parts rather than shortening the capstone.

## What was cut from the 10-part version

- A standalone knowledge-representation history article (now compressed into Part 1).
- A standalone "why the Semantic Web stalled" essay (now the opening of Part 2).
- A standalone Palantir comparison (a paragraph in Part 5; expand into a follow-up article if the series lands).
- Standalone industry survey and synthesis articles (sidebar and decision guide in Part 5; the OntoBricks standards-import feature carries FIBO, CDISC, and IOF concretely).

## Caveats

- Genie Ontology is in Preview. Features can change. Genie One is GA. Part 5 labels preview status clearly.
- OntoBricks is a databrickslabs project provided AS-IS with no SLAs. Part 4 says so and pins the version used (v0.4.0+ requires Lakebase; provisioned Lakebase instances are not supported).
- Accuracy figures are vendor-run and specific to those benchmarks. The Databricks 28-question suite and the dbt ACME Insurance suite are not comparable. Both appear with caveats.
