"""Reproducible teaching lab. No language model, embedding model, or API key."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import csv
import hashlib
import importlib.metadata
import json
import re
import networkx as nx
import numpy as np
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef

ROOT = Path(__file__).resolve().parent
SAAS = Namespace('http://example.org/saas#')
AS_OF = date(2026, 8, 29)
QUESTION = ('Hooli, Vandelay, and Wayne went quiet in the usage data. '
            'Why did they stop using the product?')


def label(iri):
    return str(iri).rsplit('#', 1)[-1].rsplit('/', 1)[-1]


def nodes_of(G, kind):
    return sorted(n for n, d in G.nodes(data=True) if str(SAAS[kind]) in d['labels'])


def related(G, node, relation):
    return sorted(v for _, v, k in G.out_edges(node, keys=True) if k == str(SAAS[relation]))


def rdf_to_lpg(g):
    """Project this named-individual fixture; retain RDF separately for OWL.

    Full IRIs identify nodes, properties, and class labels. Literal arrays
    retain datatype, language, and lexical value. This is not a general
    RDF-to-LPG converter; anonymous instance data is outside its scope.
    """
    classes = {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    individuals = {s for s, _, t in g.triples((None, RDF.type, None))
                   if isinstance(s, URIRef) and t in classes and s not in classes}
    def expand(t):
        seen, todo = set(), [t]
        while todo:
            current = todo.pop()
            if current not in seen:
                seen.add(current)
                todo.extend(p for p in g.objects(current, RDFS.subClassOf) if isinstance(p, URIRef))
        return {str(t) for t in seen}
    G = nx.MultiDiGraph()
    for s in sorted(individuals):
        G.add_node(str(s), name=label(s), labels=set(), properties={})
    projected = 0
    for s, p, o in sorted(g, key=lambda t: tuple(str(x) for x in t)):
        if s not in individuals:
            continue
        if p == RDF.type and isinstance(o, URIRef) and o in classes:
            G.nodes[str(s)]['labels'].update(expand(o)); projected += 1
        elif isinstance(o, Literal):
            G.nodes[str(s)]['properties'].setdefault(str(p), []).append({
                'value': str(o), 'datatype': str(o.datatype) if o.datatype else None,
                'language': o.language})
            projected += 1
        elif o in individuals:
            G.add_edge(str(s), str(o), key=str(p)); projected += 1
    return G, {'rdf_triples': len(g), 'projected_instance_triples': projected,
               'triples_retained_only_in_rdf': len(g)-projected,
               'owl_reasoning_executed': False}


def scalar(G, node, name):
    values = G.nodes[node]['properties'].get(str(SAAS[name]), [])
    if len(values) != 1:
        raise ValueError(f'{label(node)} requires exactly one {name} value in this lab')
    value = values[0]['value']
    if name == 'isActive':
        if value not in ('true', 'false', '1', '0'):
            raise ValueError('Invalid boolean')
        return value in ('true', '1')
    if name == 'mrr':
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0:
            raise ValueError('MRR must be finite and nonnegative')
        return amount
    return value


def load_accounts(G, path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        a, s, p = (str(SAAS[row[k]]) for k in ('account', 'subscription_id', 'plan'))
        if p not in G or str(SAAS.Plan) not in G.nodes[p]['labels']:
            raise ValueError(f'Unknown plan: {row["plan"]}')
        if a in G or s in G:
            raise ValueError('Duplicate account or subscription in extension')
        if row['is_active'] not in ('true', 'false'):
            raise ValueError('Invalid subscription status')
        mrr = Decimal(row['mrr'])
        if not mrr.is_finite() or mrr < 0:
            raise ValueError('MRR must be finite and nonnegative')
        G.add_node(a, name=row['account'], labels={str(SAAS.Account)}, properties={})
        G.add_node(s, name=row['subscription_id'], labels={str(SAAS.Subscription)}, properties={
            str(SAAS.isActive): [{'value': row['is_active'], 'datatype': 'http://www.w3.org/2001/XMLSchema#boolean', 'language': None}],
            str(SAAS.mrr): [{'value': str(mrr), 'datatype': 'http://www.w3.org/2001/XMLSchema#decimal', 'language': None}]})
        G.add_edge(a, s, key=str(SAAS.hasSubscription))
        G.add_edge(s, p, key=str(SAAS.onPlan))


def load_usage(G, path, coverage, as_of=AS_OF):
    start = as_of - timedelta(days=30)
    complete_window = (date.fromisoformat(coverage['start_inclusive']) <= start
                       and date.fromisoformat(coverage['end_exclusive']) >= as_of)
    totals, last = defaultdict(int), {}
    seen = set()
    accounts = set(nodes_of(G, 'Account'))
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            account = str(SAAS[row['account']]); day = date.fromisoformat(row['date'])
            count = int(row['events'])
            if account not in accounts or count < 0 or (account, day) in seen:
                raise ValueError('Unknown account, negative count, or duplicate account/day')
            seen.add((account, day))
            if day >= as_of:  # Ignore future and current incomplete day.
                continue
            if count > 0:
                last[account] = max(last.get(account, day), day)
            if start <= day < as_of:
                totals[account] += count
    for account in sorted(accounts):
        complete = complete_window and label(account) in coverage['complete_accounts']
        G.nodes[account].update(
            events_30d=totals[account] if complete else None,
            usage_complete=complete,
            last_observed_event=last[account].isoformat() if account in last else None)
    G.graph.update(as_of=as_of.isoformat(), window_start_inclusive=start.isoformat(),
                   window_end_exclusive=as_of.isoformat(), usage_coverage=coverage)


def validate_snapshot(G):
    # Operational checks implement the fixture's shape, not OWL inference.
    owners = defaultdict(set)
    for a in nodes_of(G, 'Account'):
        subs = related(G, a, 'hasSubscription')
        if not subs:
            raise ValueError('Subscription snapshot incomplete for ' + label(a))
        for s in subs:
            owners[s].add(a)
            if len(related(G, s, 'onPlan')) != 1:
                raise ValueError('Each subscription must have one plan')
            scalar(G, s, 'isActive'); scalar(G, s, 'mrr')
    if any(len(v) != 1 for v in owners.values()):
        raise ValueError('Subscription has multiple account owners')


def contract_inactive(G):
    return [a for a in nodes_of(G, 'Account')
            if not any(scalar(G, s, 'isActive') for s in related(G, a, 'hasSubscription'))]


def usage_inactive(G):
    return [a for a in nodes_of(G, 'Account') if G.nodes[a].get('events_30d') == 0]


def active_paid_mrr(G, accounts=None):
    total, seen = Decimal('0'), set()
    for a in nodes_of(G, 'Account') if accounts is None else accounts:
        for s in related(G, a, 'hasSubscription'):
            if s not in seen and scalar(G, s, 'isActive'):
                if any(str(SAAS.PaidPlan) in G.nodes[p]['labels'] for p in related(G, s, 'onPlan')):
                    total += scalar(G, s, 'mrr'); seen.add(s)
    return total


ENTITY_TYPES = {
    'Scheduled Exports': 'Feature', 'legacy export engine': 'Component',
    'new export engine': 'Component', 'SSO': 'Feature', 'SAML': 'Protocol',
    'dashboard': 'Feature', 'REST API': 'Feature', 'webhook': 'Feature',
    'audit log': 'Feature', 'billing': 'Feature', 'Data Import': 'Feature',
    'mobile app': 'Feature', 'Free': 'Plan', 'Pro': 'Plan', 'Enterprise': 'Plan'}
ERROR_CODE = re.compile(r'\b[A-Z]{2,4}-\d{3}\b')
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]+')


def load_corpus(data_dir):
    result = []
    for filename, kind in [('tickets.jsonl', 'ticket'), ('docs.jsonl', 'doc')]:
        for line in (Path(data_dir)/filename).read_text().splitlines():
            row = json.loads(line)
            result.append({'id': row['id'], 'kind': kind, 'account': row.get('account'),
                           'date': row.get('date'), 'text': row.get('subject', row.get('title')) + '. ' + row['body']})
    return sorted(result, key=lambda s: s['id'])


def entity_key(name, kind):
    return str(SAAS[name]) if kind in ('Account', 'Plan') else f'{kind}:{name}'


def build_evidence_graph(corpus, account_names):
    """Return co-occurrence graph and mention records with exact character spans."""
    source_ids = [s['id'] for s in corpus]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError('Duplicate source identifier')
    if any(s['account'] is not None and s['account'] not in account_names for s in corpus):
        raise ValueError('Unknown account in ticket metadata')
    EG, records = nx.Graph(), []
    known = {**ENTITY_TYPES, **{a: 'Account' for a in account_names}}
    per_source = {}
    for source in sorted(corpus, key=lambda s: s['id']):
        found = set()
        if source['account']:
            records.append({'source_id': source['id'], 'entity': entity_key(source['account'], 'Account'),
                            'name': source['account'], 'kind': 'Account', 'method': 'account_metadata',
                            'span': None})
            found.add((source['account'], 'Account'))
        for name, kind in sorted(known.items()):
            for match in re.finditer(rf'\b{re.escape(name)}s?\b', source['text'], re.I):
                found.add((name, kind))
                records.append({'source_id': source['id'], 'entity': entity_key(name, kind),
                                'name': name, 'kind': kind, 'method': 'dictionary',
                                'span': [match.start(), match.end()]})
        for match in ERROR_CODE.finditer(source['text']):
            name = match.group(); found.add((name, 'ErrorCode'))
            records.append({'source_id': source['id'], 'entity': entity_key(name, 'ErrorCode'),
                            'name': name, 'kind': 'ErrorCode', 'method': 'regex',
                            'span': [match.start(), match.end()]})
        per_source[source['id']] = sorted(entity_key(n,t) for n,t in found)
        for name, kind in sorted(found):
            key = entity_key(name, kind)
            if key not in EG: EG.add_node(key, name=name, kind=kind, sources=[])
            EG.nodes[key]['sources'].append(source['id'])
    # Canonical ordering removes hash-seed dependence before randomized Louvain.
    ordered = nx.Graph()
    ordered.add_nodes_from((n, EG.nodes[n]) for n in sorted(EG))
    for source_id, entities in sorted(per_source.items()):
        for i, u in enumerate(entities):
            for v in entities[i+1:]:
                if not ordered.has_edge(u, v): ordered.add_edge(u, v, weight=0, sources=[])
                ordered[u][v]['weight'] += 1
                ordered[u][v]['sources'].append(source_id)
    return ordered, records


def detect_communities(EG):
    communities = nx.community.louvain_communities(EG, weight='weight', seed=42)
    return sorted((sorted(c) for c in communities), key=lambda c: (-len(c), c))


def tokenize(text):
    return [m.lower() for m in TOKEN.findall(text)]


def lexical_search(query, corpus, k=4):
    docs = [tokenize((s['account'] or '') + ' ' + s['text']) for s in corpus]
    vocab = {w:i for i,w in enumerate(sorted({w for d in docs for w in d}))}
    tf = np.zeros((len(docs), len(vocab)))
    for i, doc in enumerate(docs):
        for w in doc: tf[i, vocab[w]] += 1
    idf = np.log((1+len(docs))/(1+(tf>0).sum(axis=0)))+1
    matrix = tf*idf
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
    q = np.zeros(len(vocab))
    for w in tokenize(query):
        if w in vocab: q[vocab[w]] += idf[vocab[w]]
    q /= max(np.linalg.norm(q), 1e-12)
    scores = matrix @ q
    order = sorted(range(len(corpus)), key=lambda i: (-float(scores[i]), corpus[i]['id']))
    return [{'source_id':corpus[i]['id'], 'score':round(float(scores[i]),6)} for i in order[:k]]


def account_evidence(account, corpus, EG, G):
    """Explicit local traversal. Communities are exploratory, not required here.

    Account -> ticket metadata -> error mention -> help document.
    Ticket ownership never propagates through a co-occurrence community.
    """
    key = str(SAAS[account])
    if key not in nodes_of(G, 'Account'): raise ValueError('Unknown account')
    tickets = [s for s in corpus if s['kind']=='ticket' and s['account']==account]
    error_codes = sorted({c for t in tickets for c in ERROR_CODE.findall(t['text'])})
    docs = [s for s in corpus if s['kind']=='doc' and any(
        s['id'] in EG.nodes[entity_key(c, 'ErrorCode')]['sources'] for c in error_codes)]
    subs = related(G, key, 'hasSubscription')
    return {'account': account, 'account_iri': key,
            'status': {'plans': sorted({label(p) for s in subs for p in related(G,s,'onPlan')}),
                       'subscription_active': any(scalar(G,s,'isActive') for s in subs),
                       'events_30d': G.nodes[key]['events_30d'],
                       'last_observed_event': G.nodes[key]['last_observed_event']},
            'error_codes': error_codes, 'tickets': tickets, 'documents': docs,
            'interpretation_limit': 'Reported problems may explain inactivity. Causation and current incident status are not established.'}


def retrieval_comparison(corpus, accounts, EG, G):
    # Gold evidence is hand-labeled for this one synthetic teaching question.
    gold = {'T-1010','T-1012','T-1014','D-03','T-1002','T-1006','T-1013','T-1016','D-01','D-02'}
    lexical = [r['source_id'] for r in lexical_search(QUESTION, corpus)]
    metadata = sorted(s['id'] for s in corpus if s['account'] in accounts)
    expanded = sorted({s['id'] for a in accounts for field in ('tickets','documents')
                       for s in account_evidence(a,corpus,EG,G)[field]})
    by_id = {s['id']:s for s in corpus}
    def score(name, ids):
        hit = len(set(ids)&gold)
        return {'method':name, 'source_ids':ids, 'sources':len(ids),
                'whitespace_words':sum(len(by_id[i]['text'].split()) for i in ids),
                'evidence_recall':hit/len(gold), 'evidence_precision':hit/len(ids) if ids else 0}
    return [score('TF-IDF top 4',lexical), score('Account metadata',metadata),
            score('Account + error links',expanded)]


def json_ready(obj):
    if isinstance(obj, dict): return {str(k):json_ready(v) for k,v in obj.items()}
    if isinstance(obj, set): return sorted(json_ready(v) for v in obj)
    if isinstance(obj, (list, tuple)): return [json_ready(v) for v in obj]
    if isinstance(obj, Decimal): return str(obj)
    return obj


def save_outputs(G, EG, mentions, communities, corpus, projection, out_dir):
    out_dir=Path(out_dir);out_dir.mkdir(parents=True, exist_ok=True)
    def save(name,value):
        (out_dir/name).write_text(json.dumps(json_ready(value),indent=2,sort_keys=True)+'\n')
    graph_data = {'schema_version':2, **G.graph,
                  'nodes':[{'id':n,**d} for n,d in sorted(G.nodes(data=True))],
                  'edges':[{'source':u,'target':v,'type':k} for u,v,k in sorted(G.edges(keys=True))]}
    save('saas_graph.json',graph_data)
    save('projection_audit.json',projection)
    save('mentions.json',mentions)
    save('entity_graph.json', {'nodes':[{'id':n,**d} for n,d in sorted(EG.nodes(data=True))],
         'edges':[{'source':u,'target':v,**d} for u,v,d in sorted(EG.edges(data=True))]})
    save('communities.json',[[EG.nodes[n]['name'] for n in c] for c in communities])
    accounts = [label(a) for a in usage_inactive(G)]
    save('evidence_packets.json',[account_evidence(a,corpus,EG,G) for a in accounts])
    save('retrieval_comparison.json',retrieval_comparison(corpus,accounts,EG,G))
    summary={'active_paid_mrr':active_paid_mrr(G), 'contract_inactive':[label(a) for a in contract_inactive(G)],
             'usage_inactive':accounts, 'active_paid_mrr_on_inactive_accounts':active_paid_mrr(G,usage_inactive(G)),
             'accounts':len(nodes_of(G,'Account')), 'unknown_usage_accounts':[label(a) for a in nodes_of(G,'Account') if G.nodes[a]['events_30d'] is None]}
    save('results.json',summary)
    save('run_manifest.json', {'as_of':AS_OF.isoformat(), 'seed':42,
         'versions':{p:importlib.metadata.version(p) for p in ('rdflib','networkx','numpy')},
         'data_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data').iterdir()) if p.is_file()}})
    return summary


def run(out_dir=None):
    g=Graph().parse(ROOT/'data/saas_ontology.ttl',format='turtle')
    G,projection=rdf_to_lpg(g)
    load_accounts(G,ROOT/'data/accounts.csv')
    load_usage(G,ROOT/'data/usage_events.csv',json.loads((ROOT/'data/usage_coverage.json').read_text()))
    validate_snapshot(G)
    corpus=load_corpus(ROOT/'data')
    EG,mentions=build_evidence_graph(corpus,[label(a) for a in nodes_of(G,'Account')])
    communities=detect_communities(EG)
    summary=save_outputs(G,EG,mentions,communities,corpus,projection,out_dir or ROOT/'outputs')
    return g,G,EG,mentions,communities,corpus,projection,summary


if __name__=='__main__':
    *_, summary=run()
    print(json.dumps(json_ready(summary),indent=2))
