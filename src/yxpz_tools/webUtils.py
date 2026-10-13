import os
import platform
import random
from pathlib import Path

from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
]


class webSite:
    """DrissionPage 浏览器配置封装，适配 Windows 桌面 / Windows Server 堡垒机 / Linux 服务器。

    hide=False 前台运行（开发调试看得到界面），hide=True 无头后台（服务器/堡垒机）。
    """

    def __init__(self):
        self.browser = None
        self.tab_timeouts = 5
        self.the_port = 19222
        self.system = platform.system()
        # Linux 下 Chrome 可执行文件路径，机器上装的位置不同时直接改这个属性即可
        self.chrome_path = "/opt/google/chrome/google-chrome"

    def _build_options(self, hide=False, port=None):
        """统一的 ChromiumOptions 构建入口：hide 控制无头，按 OS 自动适配。"""
        co = ChromiumOptions()

        # 1. 反自动化检测
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.set_argument("--exclude-switches=enable-automation")  # 等效于 excludeSwitches
        co.set_argument("--disable-automation-extension")

        # 2. 服务器/容器友好参数（Linux root 下 --no-sandbox 必需）
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")
        co.set_argument("--disable-gpu")
        co.set_argument("--disable-features=Prerender2")
        co.set_argument("--start-maximized")
        co.set_argument("--blink-settings=imagesEnabled=true")

        # 3. 随机 User-Agent + 模拟真实浏览器指纹
        co.set_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        co.set_argument("--lang=en-US,en;q=0.9")
        co.set_argument("--accept-language=en-US,en;q=0.9")
        co.set_argument("--referrer=https://www.google.com/")

        # 4. 无头开关（唯一入口：hide=False 时绝不带 --headless=new）
        co.headless(hide)
        if hide:
            co.set_argument("--headless=new")

        # 5. 端口：DP 通过端口接管浏览器
        if port is None:
            self.the_port = co.auto_port()
        else:
            co.set_local_port(port)
            self.the_port = port

        # 6. 按操作系统适配
        if self.system == 'Windows':
            # Windows 桌面 / Windows Server 堡垒机
            co.set_user_data_path(os.path.join(os.environ["USERPROFILE"], '.chrome_auto_date'))
            # 禁用强制门户检测，杜绝"连接到网络"插页和 gstatic 报错标签页（堡垒机常见）
            co.set_pref('captive_portal_info.enabled', False)
            # 内网自签证书：解决"您的连接不是私密连接"插页
            co.ignore_certificate_errors(True)
        elif self.system == 'Linux':
            # Linux 服务器：指定 Chrome 路径，数据目录放到用户家目录解决权限问题
            co.set_paths(browser_path=self.chrome_path)
            user_data_path = Path.home() / '.chrome_date'
            print(f'设置chrome目录：{user_data_path}')
            os.makedirs(user_data_path, exist_ok=True)
            co.set_user_data_path(user_data_path)

        return co

    def init_config(self, port=None):
        """兼容别名：旧的 init_config 语义就是无头模式。"""
        return self._build_options(hide=True, port=port)

    def getChromeBrowser(self, hide=False, port=9222):
        '''
        :param hide: True 无头后台运行，False 前台显示
        :param port: 浏览器端口，DP 通过端口接管浏览器
        '''
        print(f'===========系统环境：{self.system}============')
        self.browser = ChromiumPage(self._build_options(hide=hide, port=port))
        return self.browser

    def open_web(self, hide=False, port=9222):
        '''指定端口生成 tab'''
        browser = self.getChromeBrowser(hide, port)
        tab = browser.latest_tab
        tab.set.timeouts(self.tab_timeouts)  # 全局设置查找元素超时时间
        return tab

    def get_new_browser_tab(self, hide=True, port=None):
        '''新建浏览器并返回 tab。hide 默认 True 保持该方法历来无头的语义。'''
        self.browser = ChromiumPage(self._build_options(hide=hide, port=port))
        tab = self.browser.latest_tab
        tab.set.timeouts(self.tab_timeouts)
        return tab

    def quit(self):
        if self.browser:
            self.browser.quit()
            print('浏览器退出成功')
