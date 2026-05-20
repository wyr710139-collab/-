import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urljoin
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import os

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CostcoCrawler:
    def __init__(self):
        self.base_url = "https://www.costco.com.tw/search"
        self.products = []
        # 初始化 Selenium WebDriver
        self.driver = None
        self.init_driver()
        
    def init_driver(self):
        """初始化WebDriver"""
        try:
            options = webdriver.ChromeOptions()
            # options.add_argument('--headless')  # 如果需要無頭模式，可以取消註釋
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            logger.error(f"初始化WebDriver失敗: {e}")
            raise
        
    def fetch_page(self, page_num=1, retry=3):
        """使用Selenium抓取指定頁碼的數據，支持重試"""
        # Costco網站的page參數從0開始，所以第N頁應該用 page=N-1
        api_page = page_num - 1
        full_url = f"{self.base_url}?text=餅乾&page={api_page}"
        
        for attempt in range(retry):
            try:
                logger.info(f"正在抓取第 {page_num} 頁 (嘗試 {attempt + 1}/{retry})")
                logger.info(f"  完整URL: {full_url}")
                self.driver.get(full_url)
                
                # 等待產品容器加載
                wait = WebDriverWait(self.driver, 15)
                wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'product-info-wrapper')))
                
                # 多次檢查確保所有產品都加載完成
                time.sleep(3)
                
                # 獲取頁面源碼
                page_source = self.driver.page_source
                
                # 檢查是否有實際產品
                soup = BeautifulSoup(page_source, 'html.parser')
                product_count = len(soup.find_all('div', class_='product-info-wrapper'))
                logger.info(f"第 {page_num} 頁檢測到 {product_count} 個產品")
                
                return page_source
            except TimeoutException:
                logger.warning(f"⚠ 第 {page_num} 頁加載超時 (嘗試 {attempt + 1}/{retry})")
                if attempt < retry - 1:
                    logger.info("等待5秒後重試...")
                    time.sleep(5)
                continue
            except WebDriverException as e:
                logger.warning(f"⚠ WebDriver異常: {e} (嘗試 {attempt + 1}/{retry})")
                if attempt < retry - 1:
                    logger.info("重新初始化WebDriver...")
                    try:
                        if self.driver:
                            self.driver.quit()
                    except:
                        pass
                    time.sleep(2)
                    try:
                        self.init_driver()
                    except:
                        pass
                continue
            except Exception as e:
                logger.error(f"✗ 請求失敗: {e}")
                if attempt < retry - 1:
                    time.sleep(5)
                continue
        
        logger.error(f"✗ 無法獲取第 {page_num} 頁內容，重試{retry}次後失敗")
        return None
    
    def parse_page(self, html_content):
        """解析頁面內容"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        products_on_page = []
        
        # 查找所有產品容器
        product_items = soup.find_all('div', class_='product-info-wrapper')
        
        logger.info(f"找到 {len(product_items)} 個產品容器")
        
        # 調試：如果沒找到，保存HTML用於檢查
        if len(product_items) == 0:
            logger.warning("未找到 product-info-wrapper，保存HTML文件用於調試...")
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.warning("已保存到 debug_page.html，請檢查HTML結構")
            return products_on_page
        
        for item in product_items:
            try:
                # 提取產品名稱 - 從 lister-name 鏈接中獲取
                name_link = item.find('a', class_='lister-name')
                if name_link:
                    name_span = name_link.find('span', class_='notranslate')
                    product_name = name_span.get_text(strip=True) if name_span else 'N/A'
                else:
                    product_name = 'N/A'
                
                # 提取價格
                price_span = item.find('sip-format-price')
                if price_span:
                    price_text = price_span.find('span', class_='notranslate')
                    product_price = price_text.get_text(strip=True) if price_text else 'N/A'
                else:
                    product_price = 'N/A'
                
                # 提取評分
                rating_span = item.find('span', class_='star-ratings-text')
                rating = rating_span.get_text(strip=True) if rating_span else 'N/A'
                
                logger.debug(f"找到產品: 名稱={product_name}, 價格={product_price}, 評分={rating}")
                
                product_data = {
                    '產品名稱': product_name,
                    '價格': product_price,
                    '評分': rating
                }
                products_on_page.append(product_data)
                
            except Exception as e:
                logger.warning(f"解析產品項目出錯: {e}")
                continue
        
        return products_on_page
    
    def check_has_next_page(self, html_content):
        """檢查是否有下一頁"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 多種方法檢查下一頁
        # 方法1: 查找分頁導航
        pagination = soup.find('nav', class_='pagination')
        if pagination:
            next_link = pagination.find('a', {'aria-label': 'Next'})
            if next_link and not next_link.get('disabled'):
                logger.info("✓ 檢測到下一頁鏈接（方法1: nav.pagination）")
                return True
        
        # 方法2: 查找任何有 "next" 相關的鏈接或按鈕
        all_elements = soup.find_all(['a', 'button'])
        for element in all_elements:
            aria_label = element.get('aria-label', '').lower()
            if 'next' in aria_label or 'next page' in aria_label:
                if not element.get('disabled'):
                    logger.info(f"✓ 檢測到下一頁鏈接（方法2: {element.name} with aria-label='{aria_label}'）")
                    return True
                else:
                    logger.info(f"✗ 檢測到下一頁按鈕但已禁用（{aria_label}）")
                    return False
        
        # 方法3: 查找 rel="next" 的鏈接
        next_link = soup.find('a', {'rel': 'next'})
        if next_link:
            logger.info("✓ 檢測到下一頁鏈接（方法3: rel='next'）")
            return True
        
        logger.warning("✗ 未檢測到任何下一頁鏈接，爬取結束")
        return False
    
    def crawl_all_pages(self, max_pages=None):
        """爬取所有頁面"""
        page_num = 1
        
        while True:
            if max_pages and page_num > max_pages:
                logger.info(f"已到達最大頁數限制: {max_pages}")
                break
            
            logger.info(f"\n========== 開始爬取第 {page_num} 頁 ==========")
            html_content = self.fetch_page(page_num)
            
            if not html_content:
                logger.error(f"✗ 無法獲取第 {page_num} 頁內容，停止爬取")
                break
            
            # 解析當前頁面
            page_products = self.parse_page(html_content)
            
            if not page_products:
                logger.warning(f"⚠ 第 {page_num} 頁沒有找到產品")
            else:
                logger.info(f"✓ 第 {page_num} 頁找到 {len(page_products)} 個產品")
                self.products.extend(page_products)
            
            logger.info(f"累計已爬取: {len(self.products)} 個產品")
            
            # 檢查是否有下一頁
            logger.info(f"\n檢查是否有下一頁...")
            has_next = self.check_has_next_page(html_content)
            
            if not has_next:
                logger.info("已爬取所有頁面")
                break
            
            page_num += 1
            logger.info(f"準備爬取第 {page_num} 頁，等待3秒...")
            time.sleep(3)
        
        logger.info(f"\n========== 爬取完成 ==========")
        logger.info(f"總共爬取了 {len(self.products)} 個產品")
    
    def save_to_csv(self, filename='costco_products.csv'):
        """保存數據到CSV文件"""
        if self.products:
            try:
                # 使用絕對路徑並清除舊文件
                filepath = os.path.abspath(filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logger.info(f"已刪除舊文件: {filepath}")
                    except Exception as e:
                        logger.warning(f"無法刪除舊文件: {e}")
                
                df = pd.DataFrame(self.products)
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
                logger.info(f"✓ 數據已保存到 {filepath}")
                logger.info(f"✓ 總共保存了 {len(df)} 個產品")
            except Exception as e:
                logger.error(f"✗ 保存CSV文件失敗: {e}")
        else:
            logger.warning("⚠ 沒有數據可保存")
    
    def get_dataframe(self):
        """返回pandas DataFrame"""
        return pd.DataFrame(self.products)
    
    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()


def main():
    crawler = None
    try:
        # 創建爬蟲實例
        crawler = CostcoCrawler()
        
        # 爬取所有頁面
        crawler.crawl_all_pages(max_pages=None)
        
        # 保存數據
        crawler.save_to_csv('costco_products.csv')
        
        # 顯示結果
        df = crawler.get_dataframe()
        print("\n=== 爬取結果 ===")
        print(f"總共爬取了 {len(df)} 個產品")
        print("\n前10個產品:")
        print(df.head(10))
        print("\n數據已成功保存！")
    except Exception as e:
        logger.error(f"✗ 主程序異常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if crawler:
            try:
                crawler.close()
                logger.info("爬蟲已關閉")
            except Exception as e:
                logger.warning(f"關閉爬蟲時出錯: {e}")


if __name__ == "__main__":
    main()

