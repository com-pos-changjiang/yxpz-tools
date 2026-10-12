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
    def __init__(self):
        self.browser = None
        self.tab_timeouts = 5
        self.the_port = 19222
        self.system = platform.system()

    def init_config(self, port=None):
        """初始化浏览器配置"""
        co = ChromiumOptions()
        # 1. 基础隐身配置（关键：使用set_argument替代add_argument）
        co.set_argument("--disable-blink-features=AutomationControlled")  # 关闭自动化检测
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")
        co.set_argument("--disable-gpu")
        # co.set_argument("--window-size=1920,1080")  # 模拟正常窗口大小
        co.set_argument("--start-maximized")  # 窗口最大化

        # 2. 随机User-Agent
        co.set_argument(f"--user-agent={random.choice(USER_AGENTS)}")

        # 3. 模拟真实浏览器指纹
        co.set_argument("--lang=en-US,en;q=0.9")
        co.set_argument("--accept-language=en-US,en;q=0.9")
        co.set_argument("--referrer=https://www.google.com/")

        # 4. 无头模式伪装
        co.headless(True)
        co.set_argument("--headless=new")
        co.set_argument("--blink-settings=imagesEnabled=true")

        # 5. 设置浏览器路径
        print(f'当前操作系统环境：{self.system}')
        if self.system == 'Linux':
            co.set_paths(browser_path="/opt/google/chrome/google-chrome")

        # 关键：移除set_experimental_option，改用启动参数禁用自动化提示
        co.set_argument("--exclude-switches=enable-automation")  # 等效于excludeSwitches
        co.set_argument("--disable-automation-extension")  # 禁用自动化扩展
        if port is None:
            self.the_port = co.auto_port()
        else:
            co.set_local_port(port)
            self.the_port = port

        if self.system == 'Linux':
            # 解决linux服务器运行，chrome数据文件权限问题，将文件目录设置为用户所在目录
            user_data_path = Path.home() / '.chrome_date'
            print(f'设置chrome目录：{user_data_path}')
            import os
            os.makedirs(user_data_path, exist_ok=True)
            co.set_user_data_path(user_data_path)

        return co

    def getChromeBrowser(self,hide=False,port=9222):
        '''
        :param hide: 是否后台运行浏览器
        :param port: 浏览器端口，DP通过端口接管浏览器
        :return:
        '''
        options = ChromiumOptions()
        options.headless(hide)
        options.set_local_port(port)
        options.set_argument('--disable-features=Prerender2')
        print(f'===========系统环境：{self.system}============')
        if self.system == 'Windows':
            #os.environ["USERPROFILE"] 为windows 用户目录
            options.set_user_data_path(os.path.join(os.environ["USERPROFILE"],'.chrome_auto_date'))
            # 核心：禁用强制门户检测，杜绝"连接到网络"插页和那个 gstatic 报错标签页
            options.set_pref('captive_portal_info.enabled', False)
            # 内网自签证书：解决"您的连接不是私密连接"插页
            options.ignore_certificate_errors(True)

        # options.set_argument('--no-sandbox')  # 无沙盒模式
        self.browser = ChromiumPage(options)
        return self.browser

    def open_web(self,hide=False,port=9222):
        ''' 指定端口生成 tab'''
        browser = self.getChromeBrowser(hide,port)
        tab = browser.latest_tab
        tab.set.timeouts(self.tab_timeouts)  # 全局设置查找元素超时时间为4s
        # tab.screencast.set_save_path("yx20video")
        # tab.screencast.set_mode.video_mode()
        return tab

    def get_new_browser_tab(self, port=None):
        self.browser = ChromiumPage(self.init_config(port=port))
        tab = self.browser.latest_tab
        tab.set.timeouts(self.tab_timeouts)  # 全局设置查找元素超时时间为4s
        # tab.screencast.set_save_path("yx20video")
        # tab.screencast.set_mode.video_mode()
        return tab

    def quit(self):
        self.browser.quit()
        print('浏览器退出成功')
