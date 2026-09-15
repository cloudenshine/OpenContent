"""Offline, stdlib-only environment check. Does not start the kernel or read credentials."""
import argparse
import importlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import tempfile


def diagnose(runtime, vault=None, codex=None):
    runtime=Path(runtime).resolve();checks=[]
    def add(name,status,message,action=''):
        checks.append(dict(name=name,status=status,message=message,action=action))
    supported=sys.version_info >= (3,12)
    add('python','PASS' if supported else 'FAIL','Python '+'.'.join(map(str,sys.version_info[:3])),
        '' if supported else '安装 Python 3.12 或更高版本，在连接设置中填写该解释器的完整路径。')
    for module,distribution,expected in [('yaml','PyYAML','6.0.3'),('mistune','mistune','3.2.0')]:
        try:
            importlib.import_module(module);version=importlib.metadata.version(distribution)
            ok=version==expected
            add(distribution,'PASS' if ok else 'FAIL',distribution+' '+version,
                '' if ok else '使用当前选定的 Python 安装内核目录内 requirements.txt 的固定版本。')
        except Exception:
            add(distribution,'FAIL',distribution+' 未安装或无法导入',
                '使用当前选定的 Python 执行 -m pip install -r requirements.txt（从内核目录运行）。')
    missing=[name for name in ('opencontent/__main__.py','templates/CONTENT.md','requirements.txt') if not (runtime/name).is_file()]
    add('kernel','FAIL' if missing else 'PASS','内核文件不完整' if missing else '内核与模板完整',
        '重新解压完整插件包，保留 kernel 子目录。' if missing else '')
    if vault is not None:
        destination=Path(vault)
        if not destination.is_dir() or not (destination/'.obsidian').is_dir():
            add('vault','FAIL','目标不是已存在的默认配置 Obsidian Vault','选择已由 Obsidian 打开且包含 .obsidian 目录的仓库。')
        else:
            try:
                # A transient empty probe, removed on close; no note or settings reads/writes.
                with tempfile.TemporaryFile(prefix='.opencontent-doctor-',dir=destination) as handle:
                    handle.write(b'probe');handle.flush()
                add('vault','PASS','Vault 可写；没有读取笔记或账号配置')
            except OSError:
                add('vault','FAIL','Vault 无法写入','检查仓库目录权限、只读状态或磁盘空间后重试。')
    candidate=codex.strip() if codex else 'codex'
    executable=shutil.which(candidate)
    add('codex','PASS' if executable else 'WARN','找到 Codex 可执行文件；未检查登录' if executable else '未找到 Codex（可无 AI 使用）',
        '需要 AI 时，在项目指令台启用已安装并登录的 Codex 或 Claude。' if not executable else '')
    add('cli-login','NOT_CHECKED','没有调用模型、检测登录或读取任何凭据','在 CLI 自身完成登录，再通过插件执行一轮所选资料的任务。')
    return {'schema':1,'passed':not any(c['status']=='FAIL' for c in checks),'checks':checks,
            'network_used':False,'notes_read':False,'credentials_read':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',default=str(Path(__file__).resolve().parent))
    parser.add_argument('--vault');parser.add_argument('--codex')
    args=parser.parse_args();result=diagnose(args.runtime,args.vault,args.codex)
    # ASCII JSON works on Windows even when console and subprocess use different encodings.
    print(json.dumps(result,ensure_ascii=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
