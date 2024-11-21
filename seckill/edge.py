#!/usr/bin/env python3
# encoding=utf-8

import os
import json
import platform
import seckill.settings as utils_settings
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

# 最大重试次数
max_retry_count = 30
# 商品标题
product_name_title = "超越音符：林俊杰20周年 首部个人传记 - 限量珍藏版 书"

def default_edge_path():
    driver_dir = getattr(utils_settings, "DRIVER_DIR", None)
    if platform.system() == "Windows":
        if driver_dir:
            return os.path.abspath(os.path.join(driver_dir, "msedgedriver.exe"))
        raise Exception("The msedgedriver path attribute is not found.")
    else:
        return driver_dir or "/opt/homebrew/bin/edgedriver"

class EdgeDrive:

    def __init__(self, edge_path=default_edge_path(), seckill_time=None, password=None):
        self.edge_path = edge_path
        self.seckill_time = seckill_time
        self.seckill_time_obj = datetime.strptime(self.seckill_time, '%Y-%m-%d %H:%M:%S.%f')
        self.password = password

    def start_driver(self):
        try:
            driver = self.find_edgedriver()
            if driver:
                print("WebDriver initialized successfully.")
            return driver
        except WebDriverException:
            print("Unable to find edgedriver. Please check the drive path.")
            return None

    def find_edgedriver(self):
        try:
            driver = webdriver.Edge()
        except WebDriverException:
            try:
                driver = webdriver.Edge(executable_path=self.edge_path, options=self.build_edge_options())
            except WebDriverException:
                raise
        return driver

    def build_edge_options(self):
        edge_options = EdgeOptions()
        edge_options.use_chromium = True  # 必须显式设置 Edge 使用 Chromium 内核
        edge_options.add_argument('--disable-gpu')  # 示例添加一个选项
        
        # 添加多个选项
        arguments = [
            '--no-sandbox', '--disable-extensions', '--disable-popup-blocking',
            '--ignore-certificate-errors', '--start-maximized'
        ]
        edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # 避免不必要的日志
        for arg in arguments:
            edge_options.arguments.append(arg)

        return edge_options



    def login_with_cookie(self, login_url="https://www.taobao.com"):
        self.driver = self.start_driver()

        if self.driver is None:
            print("Failed to initialize the WebDriver. Exiting login method.")
            raise Exception("WebDriver initialization failed.")

        self.driver.get(login_url)

        # 加载 Cookies
        try:
            with open('./cookies.txt', 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            print("Cookies loaded successfully.")
        except FileNotFoundError:
            print("Cookies file not found. Please login manually first.")
            self.login()  # 手动登录后保存 Cookies

        self.driver.refresh()
        print("Login using cookies completed.")

    def login(self, login_url="https://www.taobao.com"):
        self.driver.get(login_url)
        while True:
            try:
                if self.driver.find_element(By.LINK_TEXT, "亲，请登录"):
                    print("请在10秒内扫码登录...")
                    self.driver.find_element(By.LINK_TEXT, "亲，请登录").click()
                    sleep(25)
                    if self.driver.find_element(By.XPATH, '//*[@id="J_SiteNavMytaobao"]/div[1]/a/span'):
                        print("登录成功，保存 Cookies")
                        self.get_cookie()
                        break
                    else:
                        print("登录失败，刷新重试...")
                        self.driver.refresh()
                        continue
            except Exception as e:
                print(str(e))
                continue

    def keep_wait(self):
        self.login_with_cookie()
        print("等待到点抢购...")

        is_checked = False  # 标记是否已经进入购物车并选择商品
        while True:
            current_time = datetime.now()
            time_diff = (self.seckill_time_obj - current_time).total_seconds()

            if time_diff > 30:  # 距离抢购时间大于30秒
                if not is_checked:  # 还未进入购物车并选择商品
                    self.driver.get("https://cart.taobao.com/cart.htm")
                    print("进入购物车页面并检查商品...")

                    try:
                        item_containers = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located((By.CLASS_NAME, "cartItemInfoContainer--wrOMc6CC"))
                        )
                        for container in item_containers:
                            title_element = container.find_element(By.CLASS_NAME, "title--dsuLK9IN")
                            print(f"商品标题：{title_element.text}")
                            if product_name_title in title_element.text:
                                checkbox = container.find_element(By.CSS_SELECTOR, "input.ant-checkbox-input")
                                if not checkbox.is_selected():
                                    checkbox.click()
                                    print(f"已选中商品：{product_name_title}")
                                is_checked = True
                                break
                    except Exception as e:
                        print(f"查找或选择商品时出错: {e}")

                    checkout_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "btn--QDjHtErD"))
                    )
                    checkout_button.click()
                    print("已点击结算按钮，跳转到订单页面...")
                else:
                    print("商品已选中，等待到30秒倒计时...")
                sleep(10)

            elif time_diff > 0:
                print(f"距离抢购时间还有 {time_diff:.3f} 秒，不再刷新页面...")
            else:
                print("时间到，开始抢购...")

    def sec_kill(self):
        self.keep_wait()
        print("进入抢购流程...")

        try:
            submit_succ = False
            retry_count = 0

            while not submit_succ and retry_count < max_retry_count:
                retry_count += 1
                now = datetime.now()
                if now >= self.seckill_time_obj:
                    print(f"开始抢购，尝试次数：{retry_count}")
                    try:
                        submit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CLASS_NAME, "btn--QDjHtErD"))
                        )
                        submit_button.click()
                        print("已点击提交订单按钮")
                        submit_succ = True
                    except Exception as e:
                        print(f"抢购失败，重试中：{e}")
                    sleep(0.001)
            if submit_succ:
                if self.password:
                    self.pay()

        except Exception as e:
            print(f"抢购过程中出现错误: {e}")

    def pay(self):
        try:
            element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'sixDigitPassword')))
            element.send_keys(self.password)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'J_authSubmit'))).click()
            print("付款成功")
        except Exception as e:
            print(f"付款失败：{e}")
        finally:
            sleep(60)
            self.driver.quit()

    def get_cookie(self):
        cookies = self.driver.get_cookies()
        with open('./cookies.txt', 'w', encoding='utf-8') as f:
            json.dump(cookies, f)
        print("Cookies 已保存")
