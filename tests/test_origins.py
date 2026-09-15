from copy import deepcopy
import hashlib
import tempfile
import threading
import unittest
from opencontent import origins,ideation
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.vault import Problem
from test_ideation import Synthesizer


class OriginTests(unittest.TestCase):
    def group(self,titles,bodies,urls=None):
        sources=[{'id':f's{i}','title':title,'content_hash':hashlib.sha256(body.encode()).hexdigest()} for i,(title,body) in enumerate(zip(titles,bodies))]
        rows=[{'body':body,'origin_digest':origins.origin_digest('---\nsource: '+url+'\n---\n'+body) if url else None} for body,url in zip(bodies,urls or [None]*len(bodies))]
        return sources,origins.annotate(sources,rows)
    def test_url_canonicalization_keeps_identity_and_hides_credentials(self):
        a=origins.origin_digest('---\nsource: https://example.com/read?id=1&utm_source=clip\n---\ntext')
        b=origins.origin_digest('---\nsource_url: https://EXAMPLE.com/read?fbclid=x&id=1#part\n---\nsummary')
        c=origins.origin_digest('---\nurl: https://example.com/read?id=2\n---\nother')
        self.assertEqual(a,b);self.assertNotEqual(a,c);self.assertEqual(len(a),64)
        self.assertIsNone(origins.origin_digest('---\nsource: https://user:secret@example.com/read\n---\ntext'))
        self.assertIsNone(origins.origin_digest('---\nsource: https://example.com:invalid/a\n---\ntext'))
    def test_original_transcript_title_variants_but_not_short_generic_names(self):
        title='新民学会如何从读书讨论走向公共行动'
        sources,groups=self.group(['get_'+title,title+'_1916575775841252448_transcript'],['不同长度的原文材料','口述整理和另一种摘要表达'])
        self.assertEqual(len(groups),1);self.assertEqual(sources[0]['family'],sources[1]['family'])
        self.assertEqual(len(self.group(['周记','周记_summary'],['本周写作观察','软件开发周记'])[1]),2)
    def test_shared_origin_groups_different_prose_but_distinct_articles_remain(self):
        sources,groups=self.group(['A','B','C'],['原始材料','另一种表达','不同研究'],['https://e.test/a?id=1','https://e.test/a?id=1&utm_medium=x','https://e.test/a?id=2'])
        self.assertEqual(len(groups),2);self.assertEqual(sources[0]['family'],sources[1]['family']);self.assertNotEqual(sources[0]['family'],sources[2]['family'])
    def test_overlapping_copy_does_not_count_twice(self):
        a=''.join('第'+str(i)+'个论点提出边界需要结合具体对象验证。' for i in range(40))
        b=a+'补充编辑说明。';c=''.join('样本'+str(i)+'使用随机抽样方案估计测量误差。' for i in range(40))
        self.assertEqual(len(self.group(['Alpha','Beta','Gamma'],[a,b,c])[1]),2)
    def setup_snapshot(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);k=Kernel(tmp.name)
        for name,body in [('甲','同一作者文章原文讨论如何设计知识创作的审查工作流程与具体边界。'),('乙','同一文章口述摘要解释有限注意力如何安排编辑核对的先后顺序。'),('丙','另一作者观察抽样测量的偏差，提出小样本不能泛化到整体群体。')]:
            url='https://e.test/original' if name!='丙' else 'https://e.test/other'
            (k.vault.root/(name+'.md')).write_text('---\nsource: '+url+'\n---\n'+body,encoding='utf-8')
        snap=ideation.load_snapshot(k,ideation.preview(k)['id']);return k,snap
    def test_candidate_same_family_excluded_while_valid_candidate_kept(self):
        k,s=self.setup_snapshot();provider=Synthesizer()
        self.assertEqual(s['stats']['source_families'],2)
        raw=provider.run(ideation.classify_request(s),None,None);mapping=ideation.validate_map(raw,s)
        response=provider.run(ideation.synthesis_request(s,mapping),None,None)
        invalid=deepcopy(response['ideas'][0]);invalid['title']='同源误用的另一个题目';invalid['question']='同一文章是否能够作为两种独立证据？'
        ids=next(g['sources'] for g in s['families'] if len(g['sources'])==2)
        invalid['sources']=[r for r in invalid['sources'] if r['id'] in ids]
        response['ideas'].insert(0,invalid);validated=ideation.validate_ideas(response,s,mapping)
        self.assertEqual(len(validated['ideas']),1);self.assertEqual(len(validated['excluded']),1)
        self.assertIn('同一资料组',validated['excluded'][0]['excluded_reason'])
        self.assertNotIn('https://e.test',str(ideation.classify_request(s)))
    def test_single_origin_stops_before_model_and_legacy_requires_refresh(self):
        k,s=self.setup_snapshot();(k.vault.root/'丙.md').unlink()
        s=ideation.load_snapshot(k,ideation.preview(k)['id']);p=Synthesizer();jobs=Jobs(k,{'synth':p});self.addCleanup(jobs.close)
        with self.assertRaisesRegex(Problem,'一个来源组'):jobs.discover(s['id'],'synth')
        with self.assertRaisesRegex(Problem,'两个不同来源组'):ideation.execute(k,s,p,threading.Event(),lambda stage:None)
        self.assertFalse(p.stages);self.assertFalse(k.board()['projects'])
        s['format']=2
        with self.assertRaisesRegex(Problem,'旧选题快照'):ideation.check_snapshot(k,s)
