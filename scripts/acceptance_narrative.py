"""Opt-in local acceptance against real supported sources/providers.

Creates only a temporary Vault unless --vault is explicitly supplied.
No provider is called unless --live-cover is selected.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opencontent.capabilities import CapabilityRuntime, PackRegistry
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.providers import activate_cli
from opencontent.vault import Problem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-market', action='store_true', help='Fetch the official Qimao daily ranking')
    parser.add_argument('--import-json', type=Path, help='Use a provenance-bearing market JSON snapshot')
    parser.add_argument('--short', action='store_true', help='Analyze an imported short-fiction snapshot')
    parser.add_argument('--live-cover', action='store_true', help='Use existing local CLI/account; may consume its quota')
    parser.add_argument('--provider', choices=['codex','claude'], default='codex')
    parser.add_argument('--vault', type=Path, help='Preserve evidence in this acceptance Vault (do not use a production Vault)')
    args = parser.parse_args()
    if not (args.live_market or args.import_json or args.live_cover):
        parser.error('Choose --live-market, --import-json, or --live-cover explicitly')
    if args.live_market and (args.import_json or args.short):
        parser.error('Live collection is supported only for the Qimao long-fiction source')
    with tempfile.TemporaryDirectory(prefix='opencontent-acceptance-') as temporary:
        root = args.vault or Path(temporary)
        kernel = Kernel(root)
        project = kernel.create_project('Narrative acceptance', 'Verify real source/image evidence', 'Author')['oc_id']
        jobs = Jobs(kernel)
        registry=PackRegistry();registry.discover([Path(__file__).resolve().parents[1]/'packs'])
        runtime=CapabilityRuntime(kernel,registry,jobs=jobs)
        base={'schema':'opencontent.creative-task.v1','project':project,'pack':'narrative','profile':'general-fiction'}
        outputs=[]
        try:
            if args.live_market or args.import_json:
                request={**base,'task':'short-scan' if args.short else 'long-scan'}
                if args.import_json: request['raw_data']=json.loads(args.import_json.read_text(encoding='utf-8'))
                else: request['source_ids']=['qimao-boy-hot-daily']
                outputs.append(runtime.execute_task(request))
            if args.live_cover:
                activate_cli(jobs,args.provider)
                outputs.append(runtime.execute_task({**base,'task':'cover','title':'深空回声','genre':'科幻','platform':'general','instruction':'深蓝宇宙中的孤独飞船，原创构图'},provider_name=args.provider))
            print(json.dumps({'passed':True,'vault':str(root) if args.vault else 'temporary (removed after check)','results':outputs},ensure_ascii=False,indent=2))
        except (Problem, OSError, ValueError) as error:
            print(json.dumps({'passed':False,'error':str(error),'completed_results':outputs},ensure_ascii=False,indent=2))
            return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
