# -Costco Taiwan Product Crawler (Costco 台灣商品爬蟲)
這是一個基於 Selenium 與 BeautifulSoup4 開發的 Costco 台灣官網商品資料爬蟲。專案針對現代電商網站常見的動態加載與反爬蟲機制進行了優化，具備極高的穩定性，適合用於電商數據分析、價格監控等情境。

目前預設關鍵字設定為 「餅乾」，會自動爬取所有分頁的商品名稱、價格與評分，並匯出為 CSV 檔案。

專案特色
動態加載處理：結合 Selenium WebDriver 與 WebDriverWait 顯式等待，確保網頁 JavaScript 渲染與 AJAX 產品列表完全載入後才進行解析。

強健的重試機制：針對網路波動、頁面加載超時 (TimeoutException) 或瀏覽器異常 (WebDriverException) 設有自動重試與自動重新初始化瀏覽器的機制。

多重分頁判定：內建 3 種不同的「下一頁」檢測邏輯（透過導航欄、Aria-label 屬性及 Rel 標籤），精準判斷爬取終點。

反爬蟲優化：透過隱藏自動化控制特徵 (AutomationControlled) 與自訂 User-Agent，降低被網站封鎖的風險。

資料自動導出：支援將結果匯出為 utf-8-sig 編碼的 CSV 檔案，確保中文在 Excel 中開啟時不會出現亂碼。
