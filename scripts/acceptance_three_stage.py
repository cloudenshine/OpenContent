"""Produce reviewable synthetic HTML/PNG/manifests; never call a real account/model.

Run from the repository with its exact-dependency Python. All materials and
Provider responses are clearly synthetic; fonts stay installed on the host.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from PIL import Image, ImageDraw
from test_kernel import response, STATEMENT
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.providers import AgentExecutionProvider
from opencontent.capabilities import CapabilityRuntime, PackRegistry
from opencontent import rendering
from opencontent.social_graphic import export_bundle
from opencontent.vault import digest

CONDITION='若样本仅有12条，结果不能推广到所有读者，也不代表因果关系。'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('.execution/cases'))
    args=parser.parse_args();repo=Path(__file__).resolve().parents[1];output=args.output.resolve()
    if not output.is_relative_to(repo) or output.exists():raise SystemExit('Use a fresh output directory inside this repository')
    output.mkdir(parents=True);k=Kernel(output/'synthetic-vault')
    pid=k.create_project('合成来源与媒介验收','验证图文生产闭环','测试审查人员')['oc_id']
    k.add(pid,'Material','合成原文',STATEMENT,{'source':'fixture:synthetic'},k.vault.token())
    for stage in ('distill','research','draft','critique'):
        req=k.request(pid,stage,[]);k.apply_result(pid,stage,response(req),req['token'],'synthetic',stage)
    original=k.board()['projects'][0]['artifacts'][0]
    material=k.add(pid,'Material','合成条件原文',CONDITION,{'source':'fixture:bounded-example'},k.vault.token())
    knowledge=k.add(pid,'Knowledge','条件边界','条件与否定必须保留',{'derived_from':[material['oc_id']]},k.vault.token())
    claim=k.add(pid,'Claim','有限样本',CONDITION,{'derived_from':[knowledge['oc_id']],'confidence':'medium'},k.vault.token())
    k.add(pid,'Evidence','合成逐字引文','仅作软件协议测试',{'claim':claim['oc_id'],'material':material['oc_id'],'quote':CONDITION,'relation':'supports'},k.vault.token())
    asset=k.vault.safe('Attachments/合成中文图.png');asset.parent.mkdir(parents=True)
    image=Image.new('RGB',(960,540),'#ede5d7');draw=ImageDraw.Draw(image)
    draw.rectangle((90,130,370,400),fill='#974634');draw.rectangle((580,130,860,400),fill='#386b78')
    draw.line((370,260,580,260),fill='#343434',width=14);image.save(asset)
    body=original['body']+'\n\n## 条件边界\n\n'+CONDITION+' [['+claim['oc_id']+']]\n\n'
    body+='- 先看原文，再看结论。\n- 否定词不能省略。\n\n> 这段引文来自合成材料，不能作为现实研究证据。\n\n'
    body+='| 项目 | 边界 |\n|---|---|\n| 样本 | 12条 |\n| 结论 | 不代表因果关系 |\n\n```python\ncount = 12\nassert count != 0\n```\n\n'
    body+='![合成图注：两组材料之间的关联，不表示因果](Attachments/合成中文图.png "保留限定条件的合成图注")'
    mother=k.add(pid,'Artifact','合成图文：来源与判断边界',body,{'derived_from':[*original['derived_from'],claim['oc_id']],'author':'synthetic:writer'},k.vault.token())
    def approve(aid):
        k.review(aid,'synthetic:independent',response({'stage':'critique','objects':[]})['axes'],True,'','明确合成的软件协议审查',k.vault.token(),expected_snapshot=k.inspect(aid)['input_snapshot'])
        k.decide(aid,'accept','合成测试人','只验证软件门禁，不能代表真实用户编辑批准。',k.vault.token())
    approve(mother['oc_id']);themes={}
    for theme in ('serif','academic','techDark'):
        built=rendering.export_build(k,mother['oc_id'],k.vault.token(),theme)
        destination=output/'image-text'/theme
        shutil.copytree(k.vault.safe(built['path']),destination)
        themes[theme]={'build_id':built['build_id'],'preview':str(destination.relative_to(output)/'preview.html')}
    class SyntheticSocial(AgentExecutionProvider):
        def capabilities(self):return {'reason':True,'web':False,'session':False,'test_only':True}
        def run(self,request,workspace,cancel_event):
            return {'mother_artifact_id':mother['oc_id'],'title':'合成小红书：把判断边界说清楚','body':mother['body'],
                    'pages':[{'role':'cover','purpose':'明确有限结论','source_excerpt':CONDITION,'claims':[claim['oc_id']],
                              'title':'样本有限，判断要有边界','body':CONDITION+'\n\n这套图文只用于软件验收。','resources':[]},
                             {'role':'explain','purpose':'对应原文及来源要求','source_excerpt':STATEMENT,'claims':original['derived_from'],
                              'title':'留住一条能复核的来源','body':STATEMENT+'\n\n读者可以查看原文，再判断是否接受。','resources':['Attachments/合成中文图.png']},
                             {'role':'boundary','purpose':'保留否定与适用条件','source_excerpt':CONDITION,'claims':[claim['oc_id']],
                              'title':'不能推广，也不代表因果','body':CONDITION+'\n\n不要把条件判断改成绝对承诺。','resources':[]}]}
    jobs=Jobs(k,{'synthetic':SyntheticSocial()})
    try:
        registry=PackRegistry();registry.discover([repo/'packs'])
        result=CapabilityRuntime(k,registry,jobs=jobs).execute_task({'schema':'opencontent.creative-task.v1','pack':'xiaohongshu','task':'social-graphic',
                    'project':pid,'artifact':mother['oc_id'],'instruction':'给初学者解释判断边界，逐页保留原文条件。明确标记为合成验收。','token':k.vault.token()},'synthetic')
        variant=result['artifact'];approve(variant['oc_id']);social=export_bundle(k,variant['oc_id'],k.vault.token())
        repeat=export_bundle(k,variant['oc_id'],k.vault.token())
        assert social['pages']==repeat['pages'] and social['path']==repeat['path']
        shutil.copytree(k.vault.safe(social['path']),output/'social-graphic')
        summary={'test_only':True,'real_model_executed':False,'real_account_written':False,'fonts_redistributed':False,
                 'image_text':themes,'social_graphic':{'status':social['status'],'pages':social['pages'],'preview':'social-graphic/preview.html'},
                 'deterministic_repeat':'PASS','native_host':'NOT_VERIFIED'}
        (output/'case-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        (output/'README.md').write_text('# 合成软件验收案例\n\n所有文字、材料、审查、批准和 Provider 响应均为合成 fixture。附件为程序绘制图，不是模型生图。PNG 页面使用本机字体渲染，未复制字体文件。没有平台投递或原生宿主验收。\n',encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=True))
    finally:jobs.close()


if __name__=='__main__':main()
