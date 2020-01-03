# encoding: utf-8

# refer: https://segmentfault.com/a/1190000018958917

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


class ChromeDriver(object):
    def __init__(self, executable_path):
        # 设置窗口大小
        # self.window_width = 1200
        # self.window_height = 675
        # 设置 chromedriver 位置
        self.executable_path = executable_path
        # 获取 driver
        self.driver = self.get_chrome_driver()

    def get_chrome_driver(self):
        # 头部
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
        # 创建参数对象
        options = webdriver.ChromeOptions()

        prefs = {
            # 开启图片
            "profile.managed_default_content_settings.images": 1,
            # 关闭 Notification
            "profile.default_content_setting_values.notifications": 2,
        }
        # 去掉
        options.add_experimental_option("useAutomationExtension", False)

        # 设置 Flash 的路径
        # options.add_argument('--ppapi-flash-version=32.0.0.171')
        # options.add_argument('--ppapi-flash-path=' + self.flash_path)
        # options.add_argument('binary_location=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        # 指定屏幕分辨率
        # options.add_argument('window-size=' + str(self.window_width) + 'x' + str(self.window_height) + '\'')

        # 最大化窗口
        options.add_argument('--start-maximized')
        # 规避bug
        options.add_argument('--disable-gpu')
        # 禁用弹出拦截
        options.add_argument('--disable-popup-blocking')
        # 隐藏自动软件
        options.add_argument('disable-infobars')
        options.add_argument('--allow-outdated-plugins')
        # 设置中文
        options.add_argument('lang=zh_CN.UTF-8')
        # 忽略 Chrome 浏览器证书错误报警提示
        options.add_argument('--ignore-certificate-errors')
        # 更换头部
        options.add_argument('user-agent=' + user_agent)
        options.add_argument('no-default-browser-check')
        # 关闭特征变量
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('prefs', prefs)
        # 创建 Chrome 对象
        driver = webdriver.Chrome(options=options, executable_path=self.executable_path)

        return driver

    def get(self, web_url):
        if not web_url: return False
        return self.driver.get(web_url)

    def add_flash_site(self, web_url):
        if not web_url: return False
        self.get("chrome://settings/content/siteDetails?site=" + web_url)
        root1 = self.driver.find_element(By.TAG_NAME, "settings-ui")
        shadow_root1 = self.expand_root_element(root1)
        root2 = shadow_root1.find_element(By.ID, "container")
        root3 = root2.find_element(By.ID, "main")
        shadow_root3 = self.expand_root_element(root3)
        root4 = shadow_root3.find_element(By.CLASS_NAME, "showing-subpage")
        shadow_root4 = self.expand_root_element(root4)
        root5 = shadow_root4.find_element(By.ID, "advancedPage")
        root6 = root5.find_element(By.TAG_NAME, "settings-privacy-page")
        shadow_root6 = self.expand_root_element(root6)
        root7 = shadow_root6.find_element(By.ID, "pages")
        root8 = root7.find_element(By.TAG_NAME, "settings-subpage")
        root9 = root8.find_element(By.TAG_NAME, "site-details")
        shadow_root9 = self.expand_root_element(root9)
        root10 = shadow_root9.find_element(By.ID, "plugins")
        shadow_root10 = self.expand_root_element(root10)
        root11 = shadow_root10.find_element(By.ID, "permission")
        Select(root11).select_by_value("allow")

    def expand_root_element(self, element):
        return self.driver.execute_script("return arguments[0].shadowRoot", element)

    def get_flash_url(self, web_url):
        if not web_url:
            return False
        self.add_flash_site(web_url)
        self.get(web_url)
        self.fit_content()

    def save_screenshot(self, filename):
        self.driver.save_screenshot(filename)

    def fit_content(self):
        html = self.driver.find_element(By.TAG_NAME, "html")
        client_width = int(html.get_attribute("clientWidth"))
        client_heigth = int(html.get_attribute("clientHeight"))
        width = self.driver.execute_script("return document.body.offsetWidth;")
        height = self.driver.execute_script("return document.body.offsetHeight;")
        window_size = self.driver.get_window_size()
        self.driver.set_window_size(window_size['width'] + (width - client_width),
                                    window_size['height'] + (height - client_heigth),
                                    "current")

    def quit_driver(self):
        self.driver.quit()
