"""Interactive local credential setup; secrets never go to argv, reports or chat."""
import argparse
import getpass
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from opencontent.kernel import Kernel
from opencontent.publishing import Publishing
from opencontent.vault import Problem, atomic, now


def check_connection(publishing, channel):
    result={'at':now(),'channel':channel,'token_status':'NOT_CHECKED',
        'draft_permission':'NOT_VERIFIED','publish_permission':'NOT_VERIFIED',
        'content_uploaded':False,'published':False}
    try:
        publishing.adapter(channel).token()
        result['token_status']='PASS'
        result['message']='账号令牌连接成功。草稿与发表权限仍需后续实际操作验证。'
    except Problem as error:
        result['token_status']='FAIL'
        result['message']=str(error)
    except Exception:
        result['token_status']='FAIL'
        result['message']='本地凭据读取或连接检查失败；请重新配置，或检查运行环境。'
    atomic(publishing.kernel.vault.safe('.opencontent/wechat-connection-check.json'),
        json.dumps(result,ensure_ascii=False,indent=2).encode('utf-8'))
    return result


def configure_interactive(publishing, existing=None):
    if not sys.stdin.isatty():
        raise Problem('请在你自己的交互终端运行；拒绝从管道或聊天中读取 AppSecret。')
    print('凭据将加密保存到此 Vault，并仅发送给微信官方 API 以验证连接。')
    name=input('公众号名称：').strip()
    appid=input('AppID（wx 开头）：').strip()
    if not name or not re.fullmatch(r'wx[0-9a-fA-F]{16}',appid):
        raise Problem('名称或 AppID 格式不正确；尚未读取或保存密钥。')
    secret=getpass.getpass('AppSecret（输入不显示）：').strip()
    if not secret:raise Problem('未输入 AppSecret，未保存配置。')
    try:
        return publishing.configure(name,appid,secret,channel_id=existing['id'] if existing else None)
    finally:
        secret=''


def main():
    parser=argparse.ArgumentParser(description='微信公众号本地加密接入与令牌检查')
    parser.add_argument('--vault',default=str(ROOT/'validation-vault'))
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--configure',action='store_true',help='重新填写账号凭据')
    mode.add_argument('--check-only',action='store_true',help='只检查已配置账号，不读取输入')
    args=parser.parse_args()
    vault=Path(args.vault).resolve()
    if not (vault/'CONTENT.md').is_file():raise Problem('请选择已经安装并初始化 OpenContent 的 Vault。')
    publishing=Publishing(Kernel(vault));channels=publishing.channels()
    print('当前 Vault：'+str(vault))
    channel=None
    if len(channels)==1:channel=channels[0]
    elif channels:
        if not sys.stdin.isatty():raise Problem('多个账号，请在交互终端选择目标账号。')
        for index,item in enumerate(channels,1):print(f'{index}. {item["name"]} ({item["appid"]})')
        choice=input('账号序号：').strip()
        if not choice.isdigit() or not 1<=int(choice)<=len(channels):raise Problem('账号选择无效')
        channel=channels[int(choice)-1]
    if args.check_only and not channel:
        print('NOT_CONFIGURED：尚未配置真实公众号，未发起任何微信请求。')
        return 2
    if args.configure or channel is None:channel=configure_interactive(publishing,channel)
    result=check_connection(publishing,channel['id'])
    print(result['token_status']+'：'+result['message'])
    print('检查结果保存在 Vault/.opencontent/wechat-connection-check.json；不含密钥或令牌。')
    if result['token_status']=='PASS':
        print('请回到 Codex 告知“账号已连接”。后续先核对可公开稿件及封面，再进行草稿投递验收。')
    else:
        print('若为 IP 白名单问题，请在微信后台添加当前出口 IP 后重新运行本工具。')
        print('若凭据需修改，用“Connect-WeChat.cmd --configure”重新配置；不要重置仍在使用的密钥。')
    return 0 if result['token_status']=='PASS' else 1


if __name__=='__main__':
    try:sys.exit(main())
    except (Problem,EOFError,KeyboardInterrupt) as error:
        print(str(error) if isinstance(error,Problem) else '已取消，没有完成接入。')
        sys.exit(2)
