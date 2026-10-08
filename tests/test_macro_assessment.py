"""Production engine acceptance cases T01–T40, T43–T48; fixed oracle."""
from copy import deepcopy
from datetime import timedelta
from itertools import product
import json
from pathlib import Path
import unittest

from eco import calendar as cal
from eco import macro_assessment as m

ROOT=Path(__file__).resolve().parents[1]
RULES=json.loads((ROOT/'configs/macro/macro-cross-v1.0.1.json').read_bytes())
NOW='2026-10-08T15:00:00Z'
CPI='cpi_headline_mom_sa'; CORE='pce_core_mom_sa'; HEAD='pce_headline_mom_sa'
NFP='nfp_change_k_sa'; UR='unemployment_rate_sa'; JOLTS='jolts_openings_k_sa'
GDP='real_gdp_qoq_saar'; CLAIMS='initial_claims_k_sa'; PPI='ppi_final_demand_mom_sa'; TRADE='trade_balance_bn_sa'


def fixture(values=None):
    c={'schema_version':'1.1.0','calendar_version':'us-macro-calendar-v1.1.0','scope':'US_major_macro','release_id':'calendar-'+'a'*20,'generated_at':NOW,'private_backup':{'verified':True},'sources':{},'events':[]}
    observations=[]
    for index,(metric,pair) in enumerate((values or {}).items()):
        r=RULES['registry'][metric]; actual,previous=pair
        period='2026-Q2' if metric==GDP else '2026-10-03' if metric==CLAIMS else '2026-09'
        event='employment' if metric in {NFP,UR} else metric
        scheduled='2026-10-08T12:30:00Z' if metric==CLAIMS else '2026-10-02T12:30:00Z'
        source={'sha256':str(index%10)*64,'source_url':'https://www.bea.gov/fixture/'+metric}
        c['sources'][metric]=source
        if not any(e['id']==event for e in c['events']):c['events'].append({'id':event,'kind':'jobs' if metric in {NFP,UR} else metric,'actual':actual,'scheduled_at':scheduled,'data_status':'official_release'})
        observations.append({'observation_id':'obs-'+f'{index:020x}','event_id':event,'release_family_id':'employment_report' if metric in {NFP,UR} else metric,
            'metric_id':metric,**{k:r[k] for k in ('provider','series_id','unit','transform','seasonal_adjustment')},
            'actual':actual,'previous':previous,'reference_period':period,'previous_period':m.prior_period(period),'period_end':m.period_end(period).isoformat(),
            'previous_semantics':'prior_period_same_measure','usable_at':NOW,'source_retrieved_at':NOW,'scheduled_at':scheduled,
            'source_published_at':None,'first_seen_at':None,'knowledge_basis':'legacy_snapshot_generated_at','data_status':'official_release',
            'calendar_release_id':c['release_id'],**source,'source_sha256':source['sha256'],'revision_of':None,'quality_flags':[]})
    b={'schema_version':'macro-observations-v1.0.0','parser_version':'fixture-v1','calendar_release_id':c['release_id'],'calendar_sha256':cal.digest(cal.encode(c)),'ruleset_sha256':m.digest(RULES),'observations':observations}
    return b,c


def status(check=NOW,known=NOW):
    d={'last_successful_source_check_at':check,'known_at':known}
    return {'data':d,'sha256':m.digest(d),'id':'status-'+m.digest(d)[:20]}


def evaluate(values=None, mutate=None, cutoff=NOW, proof=None, previous=None):
    b,c=fixture(values)
    if mutate:mutate(b,c)
    b['calendar_sha256']=cal.digest(cal.encode(c))
    return m.assess(b,c,status() if proof is None else proof,cutoff,previous,RULES)


def signal(a,k):return next(s for s in a['signals'] if s['metric_id']==k)


class MacroEngineTests(unittest.TestCase):
    def test_T14_125_states_against_fixed_independent_oracle(self):
        f=json.loads((ROOT/'docs/fixtures/macro-cross-v1.0.1.json').read_bytes())
        self.assertEqual(m.digest(RULES),m.RULESET_SHA256)
        for i,(lindex,l),(gindex,g) in product(f['states'],enumerate(f['states']),enumerate(f['states'])):
            regime=f['regime_grid'][i][lindex][gindex]
            with self.subTest(I=i,L=l,G=g):self.assertEqual(m.route(i,l,g,RULES),(regime,tuple(f['regime_assets'][regime])))

    def test_T01_T02_T04_decimal_inclusive_and_orientation(self):
        for actual,previous,o,eps,wanted in [('0.2','0.1',1,'0.1','positive'),('0.1','0.2',1,'0.1','negative'),('200','210',-1,'10','positive'),('4.2','4.1',-1,'0.1','negative')]:
            self.assertEqual(m.direction(actual,previous,o,eps)[2],wanted)
        with self.assertRaises(ValueError):m.direction(0.2,'0.1',1,'0.1')

    def test_T03_T31_T40_claims_small_change_not_cause_of_regime(self):
        a=evaluate({CPI:('0.4','0.1'),CORE:('0.2','0.1'),HEAD:('0.3','0.1'),NFP:('29','133'),UR:('4.2','4.1'),JOLTS:('7079','7335'),CLAIMS:('197','199')})
        self.assertEqual(a['regime_id'],'R03');self.assertEqual(a['evidence_grade'],'partial')
        self.assertEqual(a['latest_event_batch']['event_context_relation'],'small_change')
        self.assertIn('weekly_move_below_threshold',a['warnings'])
        self.assertEqual(tuple(a['assets'][k]['conclusion'] for k in m.ASSETS),('mixed','mixed','adverse'))

    def test_T05_T23_missing_new_period_blocks_older_zero_is_valid(self):
        def add_old(b,c):
            old=deepcopy(b['observations'][0]);old.update(observation_id='obs-'+'f'*20,reference_period='2026-08',previous_period='2026-07',period_end='2026-08-31',actual='0.4',previous='0.1');b['observations'].append(old)
        a=evaluate({CPI:('0',None)},add_old)
        self.assertEqual(signal(a,CPI)['direction'],'unknown')
        self.assertEqual(signal(evaluate({CPI:('0','0')}),CPI)['direction'],'flat')

    def test_T06_T16_level_context_does_not_confuse_delta_with_level(self):
        a=evaluate({NFP:('29','133'),UR:('4.2','4.1'),GDP:('2.2','2.5')})
        self.assertEqual(a['axes']['labor']['direction'],'negative')
        self.assertEqual(signal(a,NFP)['level_context'],'jobs_still_added_but_slower')
        self.assertEqual(signal(a,GDP)['level_context'],'positive_growth_decelerating')

    def test_T07_employment_split_vetoes_jolts(self):
        a=evaluate({NFP:('150','100'),UR:('4.2','4.1'),JOLTS:('7400','7200'),CPI:('0.4','0.1')})
        self.assertEqual(a['axes']['labor']['direction'],'mixed');self.assertEqual(a['regime_id'],'R_CONFLICT')
        self.assertIn(m.RULE_IDS[0],[r['rule_id'] for r in a['triggered_rules']])

    def test_T08_T10_inflation_opposition_is_mixed(self):
        for values in [{CPI:('0.4','0.1'),CORE:('0.1','0.3')},{CORE:('0.1','0.3'),HEAD:('0.3','0.1')}]:
            a=evaluate({**values,NFP:('150','100')});self.assertEqual(a['axes']['inflation']['direction'],'mixed');self.assertEqual(a['regime_id'],'R_CONFLICT')

    def test_T09_core_has_precedence_and_one_pce_slot(self):
        a=evaluate({CORE:('0.2','0.2'),HEAD:('0.3','0.1')})
        self.assertEqual(a['axes']['inflation']['direction'],'flat');self.assertEqual(a['axes']['inflation']['available_slots'],1)

    def test_T11_weekly_support_cannot_override_monthly(self):
        a=evaluate({CPI:('0.4','0.1'),NFP:('29','133'),UR:('4.2','4.1'),CLAIMS:('200','210')})
        self.assertEqual(a['axes']['labor']['direction'],'negative');self.assertIn('weekly_labor_divergence',a['warnings']);self.assertEqual(a['evidence_grade'],'partial')

    def test_T12_T13_T30_supporting_only_and_trade_not_votes(self):
        for metric,pair in [(PPI,('0.4','0.1')),(CLAIMS,('200','210')),(TRADE,('-80','-100'))]:
            a=evaluate({metric:pair});self.assertEqual(a['regime_id'],'R_INSUFFICIENT');self.assertEqual(a['usable_axis_count'],0)

    def test_T15_T43_priority(self):
        self.assertEqual(m.route('unknown','positive','flat',RULES)[0],'R_ACTIVITY_ONLY')
        self.assertEqual(m.route('unknown','positive','negative',RULES)[0],'R_CONFLICT')

    def test_T17_gdp_same_quarter_estimate_excluded(self):
        a=evaluate({GDP:('2.2','2.1')},lambda b,c:b['observations'][0].update(previous_semantics='same_period_estimate'))
        self.assertEqual(signal(a,GDP)['excluded_reason'],'same_period_revision_not_growth')

    def test_T18_negative_activity_level_overrides_crypto(self):
        a=evaluate({CPI:('0.1','0.3'),NFP:('-100','-150')})
        self.assertEqual(a['regime_id'],'R04');self.assertEqual(a['assets']['crypto_risk_assets']['conclusion'],'mixed')
        self.assertEqual(a['assets']['crypto_risk_assets']['reason_ids'],[m.RULE_IDS[-1]])

    def test_T19_order_and_duplicates_do_not_add_votes(self):
        values={CPI:('0.4','0.1'),CORE:('0.2','0.1'),NFP:('29','133')}
        a=evaluate(values)
        def duplicate(b,c):b['observations']=[*reversed(b['observations']),deepcopy(b['observations'][0])]
        other=evaluate(values,duplicate)
        self.assertEqual(a['axes'],other['axes']);self.assertEqual(a['assets'],other['assets'])
        b,c=fixture(values);before=m.assess(b,c,status(),NOW,None,RULES);b['observations'].reverse()
        self.assertEqual(before,m.assess(b,c,status(),NOW,None,RULES))

    def test_T20_T21_future_observation_and_scheduled_event_not_known(self):
        a=evaluate({CPI:('0.4','0.1'),NFP:('150','100')})
        def future(b,c):
            o=deepcopy(b['observations'][0]);o.update(observation_id='obs-'+'f'*20,usable_at='2026-10-09T00:00:00Z',actual='0.0');b['observations'].append(o)
            c['events'].append({'id':'pending','kind':'cpi','actual':None,'scheduled_at':'2026-10-08T14:00:00Z','data_status':'scheduled'})
        other=evaluate({CPI:('0.4','0.1'),NFP:('150','100')},future)
        self.assertEqual(a['assets'],other['assets']);self.assertNotIn('pending',other['latest_event_batch']['event_ids'])

    def test_T22_old_period_revision_never_becomes_latest_period(self):
        def revision(b,c):
            o=deepcopy(b['observations'][0]);o.update(observation_id='obs-'+'f'*20,reference_period='2026-08',previous_period='2026-07',period_end='2026-08-31',actual='0',usable_at='2026-10-08T15:01:00Z',first_seen_at='2026-10-08T15:01:00Z',knowledge_basis='first_seen_ledger');b['observations'].append(o)
        a=evaluate({CPI:('0.4','0.1')},revision,cutoff='2026-10-08T16:00:00Z');self.assertEqual(signal(a,CPI)['reference_period'],'2026-09')

    def test_T24_T25_period_alignment(self):
        def move(b,c):
            b['observations'][0].update(reference_period='2026-07',previous_period='2026-06',period_end='2026-07-31')
        a=evaluate({CPI:('0.4','0.1'),CORE:('0.2','0.1')},move)
        self.assertEqual(signal(a,CPI)['excluded_reason'],'period_gap_excluded')
        def move_nfp(b,c):b['observations'][0].update(reference_period='2026-08',previous_period='2026-07',period_end='2026-08-31')
        a=evaluate({NFP:('150','100'),UR:('4.2','4.1')},move_nfp)
        self.assertEqual(signal(a,NFP)['excluded_reason'],'employment_period_mismatch');self.assertEqual(a['axes']['labor']['direction'],'negative')

    def test_T26_age_boundaries(self):
        for metric,pair in [(CLAIMS,('200','210')),(CPI,('0.4','0.1')),(GDP,('2.2','2.5'))]:
            b,c=fixture({metric:pair});o=b['observations'][0];end=m.period_end(o['reference_period'])
            for extra,expected in [(0,None),(1,'stale_observation')]:
                cutoff=(m.utc(NOW).replace(year=end.year,month=end.month,day=end.day)+timedelta(days=RULES['registry'][metric]['max_age_days']+extra)).isoformat()
                a=m.assess(b,c,status(cutoff,cutoff),cutoff,None,RULES);self.assertEqual(signal(a,metric)['excluded_reason'],expected)

    def test_T27_T28_T47_T48_source_status_boundaries_and_cutoff(self):
        for hours,extra,wanted in [(0,0,'fresh'),(48,0,'fresh'),(48,1,'stale')]:
            check=(m.utc(NOW)-timedelta(hours=hours,microseconds=extra)).isoformat()
            self.assertEqual(m.pipeline_state(status(check)['data'],NOW)[0],wanted)
        for proof,reason in [(status(None),'pipeline_status_unknown'),(status('2026-10-09T00:00:00Z'),'future_pipeline_status'),(status(NOW,'2026-10-07T00:00:00Z'),'invalid_pipeline_chronology')]:
            a=evaluate({CPI:('0.4','0.1'),NFP:('150','100')},proof=proof);self.assertEqual(a['regime_id'],'R_STALE');self.assertEqual(a['pipeline_reason'],reason)

    def test_T29_contract_fields_excluded(self):
        for field,value,reason in [('unit','jobs','invalid_unit'),('seasonal_adjustment','NSA','invalid_seasonal_adjustment'),('previous_semantics',None,'missing_previous_semantics')]:
            a=evaluate({CPI:('0.4','0.1')},lambda b,c:b['observations'][0].update({field:value}));self.assertEqual(signal(a,CPI)['excluded_reason'],reason)

    def test_T32_all_latest_simultaneous_events_and_peer_excludes_batch(self):
        a=evaluate({CPI:('0.4','0.1'),CORE:('0.2','0.1'),NFP:('150','100')})
        self.assertEqual(len(a['latest_event_batch']['event_ids']),3)
        for relation in a['latest_event_batch']['per_metric_relations']:self.assertEqual(relation['peer_direction'],'unknown')

    def test_T33_flat_is_neutral_and_can_be_coherent(self):
        a=evaluate({k:('0','0') for k in [CPI,CORE,NFP,UR,JOLTS,GDP]})
        self.assertEqual(a['regime_id'],'R08');self.assertEqual(a['evidence_grade'],'coherent');self.assertTrue(all(v['conclusion']=='neutral' for v in a['assets'].values()))

    def test_T34_release_hash_status_hash_ruleset_and_backup_gates(self):
        b,c=fixture({CPI:('0.4','0.1')})
        for field,value in [('calendar_sha256','0'*64),('ruleset_sha256','0'*64)]:
            bad=deepcopy(b);bad[field]=value
            with self.assertRaises(ValueError):m.assess(bad,c,status(),NOW,None,RULES)
        bad=status();bad['sha256']='0'*64
        with self.assertRaises(ValueError):m.assess(b,c,bad,NOW,None,RULES)
        rules=deepcopy(RULES);rules['registry'][CPI]['epsilon']='0.2'
        with self.assertRaises(ValueError):m.assess(b,c,status(),NOW,None,rules)
        bad=deepcopy(b);bad['schema_version']='wrong'
        with self.assertRaises(ValueError):m.assess(bad,c,status(),NOW,None,RULES)
        bad_calendar=deepcopy(c);bad_calendar['schema_version']='wrong'
        with self.assertRaises(ValueError):m.assess(b,bad_calendar,status(),NOW,None,RULES)

    def test_T35_T37_T45_T46_cache_recovery_ids_real_predecessor(self):
        b,c=fixture({CPI:('0.4','0.1'),NFP:('150','100')})
        a=m.assess(b,c,status(),NOW,None,RULES);self.assertEqual(a['context_transition'],'not_computable')
        fresh='2026-10-08T16:00:00Z';cached=m.assess(b,c,status(fresh,fresh),fresh,a,RULES);self.assertEqual(a,cached)
        later='2026-10-11T16:00:00Z';stale=m.assess(b,c,status(NOW,later),later,a,RULES)
        recovery=m.assess(b,c,status(later,later),later,stale,RULES)
        self.assertEqual(recovery['state_id'],a['state_id']);self.assertNotEqual(recovery['assessment_id'],a['assessment_id'])
        self.assertEqual(recovery['previous_assessment_id'],stale['assessment_id']);self.assertEqual(recovery['change_reason'],'pipeline_status_changed');self.assertEqual(recovery['context_transition'],'context_only')
        self.assertEqual(recovery,m.assess(b,c,status(later,later),later,stale,RULES))

    def test_T36_T38_T44_revision_and_multiple_input_transitions(self):
        values={CPI:('0.4','0.1'),NFP:('29','133'),UR:('4.2','4.1')};b,c=fixture(values)
        # Employment event is the latest batch; CPI is older.
        c['events'][0]['scheduled_at']='2026-10-01T12:30:00Z';b['observations'][0]['scheduled_at']=c['events'][0]['scheduled_at'];b['calendar_sha256']=cal.digest(cal.encode(c))
        a=m.assess(b,c,status(),NOW,None,RULES)
        for changed,transition in [([1,2],'latest_batch_only'),([0,1],'multiple_inputs_changed')]:
            other=deepcopy(b)
            for idx in changed:
                o=other['observations'][idx];o.update(revision_of=o['observation_id'],observation_id='obs-'+f'{idx+100:020x}',actual='1')
            newer=m.assess(other,c,status(),NOW,a,RULES)
            self.assertEqual(newer['context_transition'],transition);self.assertEqual(newer['change_reason'],'source_revision');self.assertEqual(len(newer['changed_observations']),2)

    def test_T39_ambiguous_vintage_and_revision_leaf(self):
        def conflicting(b,c):
            o=deepcopy(b['observations'][0]);o.update(observation_id='obs-'+'f'*20,actual='0');b['observations'].append(o)
        a=evaluate({CPI:('0.4','0.1')},conflicting);self.assertEqual(signal(a,CPI)['excluded_reason'],'ambiguous_vintage')
        def lineage(b,c):conflicting(b,c);b['observations'][-1]['revision_of']=b['observations'][0]['observation_id']
        a=evaluate({CPI:('0.4','0.1')},lineage);self.assertEqual(signal(a,CPI)['actual'],'0')

    def test_T36_observation_expiry_changes_state_without_new_observation(self):
        b,c=fixture({CPI:('0.4','0.1'),NFP:('150','100'),CLAIMS:('200','210')})
        a=m.assess(b,c,status(),NOW,None,RULES);cutoff='2026-10-25T15:00:00Z'
        expired=m.assess(b,c,status(cutoff,cutoff),cutoff,a,RULES)
        self.assertEqual(signal(expired,CLAIMS)['excluded_reason'],'stale_observation')
        self.assertEqual(expired['change_reason'],'freshness_expired');self.assertEqual(expired['context_transition'],'context_only')
        self.assertNotEqual(expired['assessment_id'],a['assessment_id']);self.assertEqual(expired['changed_observation_ids'],[])

    def test_nonconsensus_and_unobserved_conditions_always_explicit(self):
        a=evaluate({CPI:('0.4','0.1'),NFP:('29','133')})
        self.assertEqual(a['surprise']['status'],'unavailable');self.assertEqual(a['market_confirmation']['status'],'not_measured')
        self.assertTrue(all(x['conditional'] and x['unobserved_conditions'] for x in a['assets'].values()))
        self.assertTrue(all(s['actual'] is None or isinstance(s['actual'],str) for s in a['signals']))


if __name__=='__main__':unittest.main()
