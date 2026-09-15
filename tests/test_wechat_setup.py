import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from opencontent.kernel import Kernel
from opencontent.publishing import Publishing
from opencontent.publishing_adapters import RemoteRejected
from opencontent.vault import Problem
from scripts.connect_wechat import check_connection, configure_interactive


class WeChatSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.kernel=Kernel(self.tmp.name);self.api=Mock();self.api.identity.return_value={'appid':'wx0123456789abcdef'}
        self.publishing=Publishing(self.kernel,{'fixture':self.api})

    def test_token_success_does_not_claim_draft_permission_or_publish(self):
        self.api.token.return_value='SENSITIVE_TEST_TOKEN'
        result=check_connection(self.publishing,'fixture')
        self.assertEqual(result['token_status'],'PASS')
        self.assertEqual(result['publish_permission'],'NOT_VERIFIED')
        self.assertFalse(result['published']);self.api.add_draft.assert_not_called();self.api.submit.assert_not_called()
        data=(Path(self.tmp.name)/'.opencontent/wechat-connection-check.json').read_text(encoding='utf-8')
        self.assertNotIn('SENSITIVE_TEST_TOKEN',data)

    def test_connection_failure_is_recorded_without_raw_exception_secret(self):
        self.api.token.side_effect=RuntimeError('RAW_TEST_SECRET')
        result=check_connection(self.publishing,'fixture')
        self.assertEqual(result['token_status'],'FAIL');self.assertNotIn('RAW_TEST_SECRET',json.dumps(result))

    def test_expected_wechat_error_remains_actionable(self):
        self.api.token.side_effect=RemoteRejected('微信接口错误 40164：请配置当前出口 IP 白名单。')
        result=check_connection(self.publishing,'fixture')
        self.assertIn('40164',result['message']);self.assertFalse(result['content_uploaded'])

    def test_noninteractive_secret_entry_refused(self):
        with patch('scripts.connect_wechat.sys.stdin.isatty',return_value=False),patch('scripts.connect_wechat.getpass.getpass') as password:
            with self.assertRaises(Problem):configure_interactive(self.publishing)
            password.assert_not_called()


if __name__=='__main__':unittest.main()
