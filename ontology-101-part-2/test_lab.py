"""Regression checks for data, identity, time-window, and evidence semantics."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from rdflib import Graph, RDF, OWL, Literal, Namespace
from lab import *

class LabChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g, cls.G, cls.EG, cls.mentions, cls.communities, cls.corpus, cls.audit, cls.summary = run()

    def test_reference_results(self):
        self.assertEqual(self.audit['rdf_triples'], 79)
        self.assertEqual(self.audit['projected_instance_triples'], 15)
        self.assertEqual((self.G.number_of_nodes(), self.G.number_of_edges()), (23,20))
        self.assertEqual(active_paid_mrr(self.G), Decimal('22350'))
        self.assertEqual([label(a) for a in contract_inactive(self.G)], ['Initech','Vandelay'])
        self.assertEqual([label(a) for a in usage_inactive(self.G)], ['Hooli','Vandelay','Wayne'])
        self.assertEqual(active_paid_mrr(self.G, usage_inactive(self.G)),Decimal('6200'))

    def test_part1_declarations_restored(self):
        self.assertIn((SAAS.isActive,RDF.type,OWL.FunctionalProperty),self.g)
        restrictions = list(self.g.objects(SAAS.Initech, RDF.type))
        self.assertTrue(any((r,OWL.onProperty,SAAS.hasSubscription) in self.g and
                            any(self.g.objects(r,OWL.allValuesFrom)) for r in restrictions))
        # Checking these triples is not a reasoner run.
        self.assertNotIn((SAAS.Initech,RDF.type,SAAS.Churned),self.g)

    def test_same_local_name_keeps_distinct_iris_and_literal_values(self):
        g=Graph(); other=Namespace('https://another.example/')
        for s in (SAAS.Pro, other.Pro):
            g.add((SAAS.Plan,RDF.type,OWL.Class));g.add((s,RDF.type,SAAS.Plan))
        for v in (Literal('Pro',lang='en'),Literal('Professionnel',lang='fr')):
            g.add((SAAS.Pro,SAAS.displayName,v))
        G,_=rdf_to_lpg(g)
        self.assertEqual(len(G),2)
        self.assertEqual(len(G.nodes[str(SAAS.Pro)]['properties'][str(SAAS.displayName)]),2)

    def test_usage_bounds_and_positive_last_event(self):
        G=copy.deepcopy(self.G)
        coverage=G.graph['usage_coverage']
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'events.csv'
            p.write_text('date,account,events\n2026-07-29,Hooli,100\n2026-07-30,Hooli,2\n2026-08-28,Hooli,3\n2026-08-29,Hooli,100\n2026-09-01,Hooli,100\n2026-08-27,Wayne,0\n')
            load_usage(G,p,coverage)
        self.assertEqual(G.nodes[str(SAAS.Hooli)]['events_30d'],5)
        self.assertEqual(G.nodes[str(SAAS.Hooli)]['last_observed_event'],'2026-08-28')
        self.assertIsNone(G.nodes[str(SAAS.Wayne)]['last_observed_event'])
        self.assertEqual(G.nodes[str(SAAS.Wayne)]['events_30d'],0)

    def test_incomplete_usage_is_unknown(self):
        G=copy.deepcopy(self.G);coverage=copy.deepcopy(G.graph['usage_coverage'])
        coverage['complete_accounts'].remove('Hooli')
        load_usage(G,ROOT/'data/usage_events.csv',coverage)
        self.assertIsNone(G.nodes[str(SAAS.Hooli)]['events_30d'])
        self.assertNotIn(str(SAAS.Hooli),usage_inactive(G))
        coverage['end_exclusive']='2026-08-28'
        load_usage(G,ROOT/'data/usage_events.csv',coverage)
        self.assertEqual(usage_inactive(G),[])

    def test_duplicate_usage_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'events.csv';p.write_text('date,account,events\n2026-08-01,Hooli,2\n2026-08-01,Hooli,3\n')
            with self.assertRaises(ValueError):load_usage(copy.deepcopy(self.G),p,self.G.graph['usage_coverage'])

    def test_missing_status_and_multiple_plan_are_rejected(self):
        G=copy.deepcopy(self.G)
        G.nodes[str(SAAS.Sub_001)]['properties'].pop(str(SAAS.isActive))
        with self.assertRaises(ValueError):validate_snapshot(G)
        G=copy.deepcopy(self.G)
        G.add_edge(str(SAAS.Sub_001),str(SAAS.Pro),key=str(SAAS.onPlan))
        with self.assertRaises(ValueError):validate_snapshot(G)

    def test_source_spans_and_ownership(self):
        by_id={s['id']:s for s in self.corpus}
        for m in self.mentions:
            if m['span']:
                a,b=m['span'];span=by_id[m['source_id']]['text'][a:b]
                self.assertIn(span.lower(),(m['name'].lower(),m['name'].lower()+'s'))
        packet=account_evidence('Vandelay',self.corpus,self.EG,self.G)
        self.assertEqual([s['id'] for s in packet['tickets']],['T-1002','T-1006'])
        self.assertEqual([s['id'] for s in packet['documents']],['D-01','D-02'])
        self.assertTrue(all(s['account']=='Vandelay' for s in packet['tickets']))

    def test_order_independent_communities(self):
        EG,_=build_evidence_graph(list(reversed(self.corpus)),list(reversed([label(a) for a in nodes_of(self.G,'Account')])))
        self.assertEqual(detect_communities(EG),self.communities)

    def test_reference_retrieval(self):
        rows=retrieval_comparison(self.corpus,['Hooli','Vandelay','Wayne'],self.EG,self.G)
        self.assertEqual([r['sources'] for r in rows],[4,7,10])
        self.assertEqual([r['evidence_recall'] for r in rows],[.2,.7,1.0])
        self.assertEqual([r['whitespace_words'] for r in rows],[170,293,518])

    def test_mentions_do_not_assert_active_incidents(self):
        source = {'id':'TEST', 'kind':'ticket', 'account':'Vandelay', 'date':'2026-08-01',
                  'text':'EXP-504 no longer occurs. EXP-504 is resolved.'}
        EG, mentions = build_evidence_graph([source], ['Vandelay'])
        edge = EG[str(SAAS.Vandelay)][entity_key('EXP-504','ErrorCode')]
        self.assertEqual(edge['weight'], 1)
        self.assertEqual(edge['sources'], ['TEST'])
        self.assertEqual(len([m for m in mentions if m['kind']=='ErrorCode']), 2)
        self.assertNotIn('active_incident', EG.nodes[entity_key('EXP-504','ErrorCode')])

    def test_duplicate_source_and_unknown_owner_rejected(self):
        with self.assertRaises(ValueError):
            build_evidence_graph(self.corpus + [self.corpus[0]], [label(a) for a in nodes_of(self.G,'Account')])
        bad = copy.deepcopy(self.corpus)
        next(s for s in bad if s['kind']=='ticket')['account']='Unknown'
        with self.assertRaises(ValueError):
            build_evidence_graph(bad, [label(a) for a in nodes_of(self.G,'Account')])

    def test_invalid_rdf_money_and_nonaccount_rejected(self):
        G = copy.deepcopy(self.G)
        for value in ('NaN', 'Infinity', '-1'):
            with self.subTest(value=value):
                G.nodes[str(SAAS.Sub_001)]['properties'][str(SAAS.mrr)][0]['value']=value
                with self.assertRaises(ValueError):validate_snapshot(G)
        with self.assertRaises(ValueError):account_evidence('Pro',self.corpus,self.EG,self.G)

    def test_export_preserves_identity_and_window(self):
        doc=json.loads((ROOT/'outputs/saas_graph.json').read_text())
        self.assertEqual(doc['schema_version'],2)
        self.assertEqual(doc['window_start_inclusive'],'2026-07-30')
        self.assertEqual(doc['window_end_exclusive'],'2026-08-29')
        self.assertTrue(all(n['id'].startswith(str(SAAS)) for n in doc['nodes']))
        self.assertTrue(all(e['type'].startswith(str(SAAS)) for e in doc['edges']))

if __name__=='__main__':unittest.main(verbosity=2)
