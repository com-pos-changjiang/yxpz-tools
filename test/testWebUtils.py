# -*- coding: utf-8 -*-
"""webUtils.webSite 单元测试

运行方式（项目根目录）:
    python -m unittest test.testWebUtils -v
    python -m unittest discover -s test -v

mock 单元测试不需要本机装 Chrome；真实浏览器冒烟测试需设置环境变量:
    YXPZ_BROWSER_TEST=1 python -m unittest test.testWebUtils -v
"""
import os
import unittest
from unittest.mock import MagicMock, patch

from yxpz_tools.webUtils import webSite


def make_web_site(system):
    """构造 webSite 并指定模拟的操作系统，绕开 platform.system 真实取值。"""
    ws = webSite()
    ws.system = system
    return ws


def all_arguments(co_mock):
    """收集 mock ChromiumOptions 上 set_argument 的全部实参。"""
    return [call.args[0] for call in co_mock.set_argument.call_args_list]


class testWebUtils(unittest.TestCase):
    """_build_options 的平台适配与 hide 开关行为（全 mock，无需浏览器）。"""

    def setUp(self):
        # 每个用例都 mock 掉 ChromiumOptions，记录调用供断言
        patcher = patch('yxpz_tools.webUtils.ChromiumOptions')
        self.co_cls = patcher.start()
        self.co = self.co_cls.return_value
        self.addCleanup(patcher.stop)

    # ---------- Windows ----------

    @patch.dict(os.environ, {"USERPROFILE": r"C:\Users\tester"})
    def test_win_foreground(self):
        """Windows + hide=False: 前台启动, 无任何 headless 参数, 堡垒机适配生效"""
        ws = make_web_site('Windows')
        ws._build_options(hide=False, port=9222)

        self.co.headless.assert_called_once_with(False)
        self.assertNotIn('--headless=new', all_arguments(self.co))
        self.co.set_user_data_path.assert_called_once_with(
            os.path.join(r"C:\Users\tester", '.chrome_auto_date'))
        self.co.set_pref.assert_called_once_with('captive_portal_info.enabled', False)
        self.co.ignore_certificate_errors.assert_called_once_with(True)
        self.co.set_local_port.assert_called_once_with(9222)
        # Linux 专属配置不应出现
        self.co.set_paths.assert_not_called()

    @patch.dict(os.environ, {"USERPROFILE": r"C:\Users\tester"})
    def test_win_headless(self):
        """Windows + hide=True: 无头后台(堡垒机场景), 保留 --headless=new"""
        ws = make_web_site('Windows')
        ws._build_options(hide=True, port=9222)

        self.co.headless.assert_called_once_with(True)
        self.assertIn('--headless=new', all_arguments(self.co))

    # ---------- Linux ----------

    @patch('yxpz_tools.webUtils.os.makedirs')
    def test_linux_headless(self, makedirs_mock):
        """Linux + hide=True: 服务器无头场景, 浏览器路径/数据目录/无沙盒齐备"""
        ws = make_web_site('Linux')
        ws._build_options(hide=True, port=None)

        self.co.headless.assert_called_once_with(True)
        self.assertIn('--headless=new', all_arguments(self.co))
        self.assertIn('--no-sandbox', all_arguments(self.co))
        self.assertIn('--disable-dev-shm-usage', all_arguments(self.co))
        self.co.set_paths.assert_called_once_with(browser_path=ws.chrome_path)
        # 数据目录建到家目录下, 且确实调用了 makedirs
        user_data = self.co.set_user_data_path.call_args.args[0]
        self.assertTrue(str(user_data).endswith('.chrome_date'))
        makedirs_mock.assert_called_once()

    @patch('yxpz_tools.webUtils.os.makedirs')
    def test_linux_foreground(self, makedirs_mock):
        """Linux + hide=False: 前台调试, 不带任何 headless 参数"""
        ws = make_web_site('Linux')
        ws._build_options(hide=False, port=None)

        self.co.headless.assert_called_once_with(False)
        self.assertNotIn('--headless=new', all_arguments(self.co))

    # ---------- 端口 ----------

    def test_port_given(self):
        """显式传端口: set_local_port 生效, the_port 同步"""
        ws = make_web_site('Windows')
        ws._build_options(hide=True, port=19222)
        self.co.set_local_port.assert_called_once_with(19222)
        self.assertEqual(ws.the_port, 19222)
        self.co.auto_port.assert_not_called()

    def test_port_auto(self):
        """不传端口: auto_port 自动分配并写回 the_port"""
        self.co.auto_port.return_value = 55555
        ws = make_web_site('Windows')
        ws._build_options(hide=True, port=None)
        self.co.auto_port.assert_called_once()
        self.assertEqual(ws.the_port, 55555)
        self.co.set_local_port.assert_not_called()

    # ---------- 公共参数 ----------

    def test_common_anti_detection_args(self):
        """无论平台, 反检测基础参数都必须在"""
        ws = make_web_site('Linux')
        ws._build_options(hide=True, port=None)
        args = all_arguments(self.co)
        for expected in ('--disable-blink-features=AutomationControlled',
                         '--exclude-switches=enable-automation',
                         '--no-sandbox'):
            self.assertIn(expected, args)
        # 随机 UA 一定带上了
        self.assertTrue(any(a.startswith('--user-agent=') for a in args))

    def test_init_config_is_headless_alias(self):
        """旧接口 init_config 兼容: 等价于 hide=True"""
        ws = make_web_site('Windows')
        ws.init_config(port=1234)
        self.co.headless.assert_called_once_with(True)
        self.assertIn('--headless=new', all_arguments(self.co))
        self.co.set_local_port.assert_called_once_with(1234)

    # ---------- 浏览器生命周期 ----------

    @patch('yxpz_tools.webUtils.ChromiumPage')
    @patch.dict(os.environ, {"USERPROFILE": r"C:\Users\tester"})
    def test_get_chrome_browser_returns_page(self, page_cls):
        """getChromeBrowser 返回 ChromiumPage 并挂到 self.browser"""
        ws = make_web_site('Windows')
        browser = ws.getChromeBrowser(hide=True, port=9222)
        self.assertIs(browser, page_cls.return_value)
        self.assertIs(ws.browser, browser)

    def test_quit_guard(self):
        """quit: browser 未启动时不抛异常; 已启动时调用 browser.quit()"""
        ws = make_web_site('Windows')
        ws.quit()  # 不应抛 AttributeError

        ws.browser = MagicMock()
        ws.quit()
        ws.browser.quit.assert_called_once()


@unittest.skipUnless(os.environ.get('YXPZ_BROWSER_TEST'),
                     '设置 YXPZ_BROWSER_TEST=1 运行真实浏览器冒烟(需要本机 Chrome)')
class testRealBrowser(unittest.TestCase):
    """集成冒烟: 真实启动无头浏览器再退出, 验证无头链路真实可跑。"""

    def test_headless_launch_and_quit(self):
        ws = webSite()
        tab = ws.open_web(hide=True, port=19300)
        tab.get('https://example.com')
        self.assertIn('Example', tab.title)
        ws.quit()


if __name__ == '__main__':
    unittest.main()

