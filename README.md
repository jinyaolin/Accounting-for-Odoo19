# Taiwan Accounting Localization for Odoo 19

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-green.svg)](https://www.odoo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)

完整的台灣會計本地化模組，符合台灣稅法和貿易公司需求的 Odoo 19 會計解決方案。

## 🎯 專案特色

- 🇹🇼 **台灣稅法 100% 合規** - 完全符合台灣商業會計法和稅法規定
- 🤖 **智能發票系統** - B2B/B2C 自動判斷，減少人工錯誤
- 📱 **多元載具支援** - 手機條碼、自然人憑證、愛心碼
- 🌏 **貿易會計專用** - 針對進出口貿易公司設計
- 📊 **完整報表體系** - 台灣格式財務報表

## ✨ 核心功能

### 1. 統一發票系統
- ✅ 二聯式/三聯式發票開立
- ✅ 發票字軌管理（每2個月一期）
- ✅ 自動發票號碼生成
- ✅ 買賣方統編欄位
- ✅ 課稅別選擇（應稅、零稅率、免稅）
- ✅ 發票作廢與折讓功能

### 2. B2B/B2C 自動判斷
- ✅ 根據客戶統編自動判斷發票類型
- ✅ B2B 自動帶入統編和客戶名稱
- ✅ B2C 支援多種載具類型
- ✅ 智能欄位顯示隱藏

### 3. 載具管理系統
- ✅ 客戶預設載具設定
- ✅ 手機條碼（20碼格式）
- ✅ 自然人憑證（16碼格式）
- ✅ 愛心碼（7碼格式 + 捐贈單位）
- ✅ 載具格式驗證
- ✅ 載具使用歷史記錄

### 4. 愛心碼特殊處理
- ✅ 必須選擇捐贈單位
- ✅ 自動顯示捐贈單位名稱
- ✅ 特殊列印格式
- ✅ 捐贈金額統計

### 5. 營業稅管理
- ✅ 多種稅率支援（5%、零稅率、免稅）
- ✅ 五舍六入計算邏輯
- ✅ 銷項稅額計算
- ✅ 進項稅額計算
- ✅ 應納稅額/溢付稅額計算

## 🚀 快速開始

### 系統需求

- **Odoo**: 19.0 Community Edition
- **Python**: 3.11+
- **PostgreSQL**: 14+

### 安裝步驟

```bash
# 1. 下載模組
git clone https://github.com/jinyaolin/Accounting-for-Odoo19.git
cd Accounting-for-Odoo19

# 2. 複製到 Odoo addons 目錄
cp -r tw_accounting /path/to/odoo/addons/

# 3. 更新模組列表
./odoo-bin -c odoo.conf -d database -u all --stop-after-init

# 4. 安裝模組
./odoo-bin -c odoo.conf -d database -i tw_accounting
```

### 基本設定

1. **設定客戶預設載具**
   - 進入客戶資料 → Taiwan Invoice Settings
   - 填寫統一編號（如有）
   - 選擇預設載具類型

2. **開立統一發票**
   - 建立新發票
   - 系統自動判斷 B2B/B2C
   - 自動帶入客戶預設載具

3. **查看載具記錄**
   - 發票確認後自動記錄
   - 可查看使用歷史和統計

## 🏗️ 技術架構

### 模組結構

```
tw_accounting/
├── models/              # 資料模型
│   ├── account_account.py        # 會計科目擴展
│   ├── tw_partner.py              # 客戶台灣化
│   ├── tw_invoice.py              # 發票台灣化
│   ├── tw_carrier_history.py      # 載具歷史
│   └── tw_donation_unit.py        # 愛心碼捐贈單位
├── views/               # 視圖定義
│   ├── tw_account_views.xml
│   ├── tw_partner_views.xml
│   ├── tw_invoice_views.xml
│   └── tw_menu.xml
├── security/            # 權限設定
└── data/               # 基礎資料
```

### 模型繼承策略

採用 **Odoo 最佳實踐**，繼承核心模型而非創建新模型：

```python
class AccountMove(models.Model):
    _inherit = 'account.move'  # 繼承 Odoo 核心發票模型

class ResPartner(models.Model):
    _inherit = 'res.partner'   # 繼承 Odoo 核心客戶模型
```

## 📅 開發階段

- **Phase 1** (Week 1-4): 核心合規與發票開立 ✅ 進行中
- **Phase 2** (Week 5-8): 稅務申報與貿易特性
- **Phase 3** (Week 9-12): 進階功能與優化

## 🎨 使用者介面

### 客戶設定介面
- 統一編號設定
- 預設載具選擇
- 載具使用歷史

### 發票開立介面
- 自動判斷發票類型
- 動態顯示對應欄位
- 智能欄位驗證

### 愛心碼處理
- 捐贈單位下拉選單
- 自動顯示單位名稱
- 特殊格式列印

## 📊 功能演示

### B2B/B2C 自動判斷

```python
# 有統編的客戶
客戶: ABC 貿易公司
統編: 12345678
→ 自動判斷為 B2B 三聯式
→ 自動帶入統編和公司名稱

# 無統編的客戶
客戶: 王小明
統編: (空)
→ 自動判斷為 B2C 二聯式
→ 根據客戶預設帶入載具
```

### 載具預設流程

```python
# 客戶預設: 手機條碼
載具編號: /ABC123456789012345
→ 每次開立發票自動帶入
→ 減少重複輸入

# 客戶預設: 每次詢問
→ 每次開立發票時清空
→ 讓會計人員手動選擇
```

## 🔐 安全性

- ✅ 多級權限管理
- ✅ 欄位格式驗證
- ✅ 統一編號邏輯驗證
- ✅ 載具編號格式檢查

## 📚 文檔

完整的需求規格和技術文檔請參考：

- [需求規格書](https://github.com/jinyaolin/odoo19/blob/main/TAIWAN_ACCOUNTING_REQUIREMENTS.md)
- [技術架構](https://github.com/jinyaolin/odoo19/blob/main/TAIWAN_ACCOUNTING_PLAN_V2.md)
- [開發計劃](https://github.com/jinyaolin/Accounting-for-Odoo19)

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

1. Fork 本專案
2. 建立特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 LGPL-3 授權 - 詳見 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

**jinyaolin**

## 📞 聯絡方式

- **GitHub**: [@jinyaolin](https://github.com/jinyaolin)
- **Email**: jinyao.lin@gmail.com

## 🙏 致謝

- Odoo 社群
- 台灣會計師公會
- 所有測試用戶

---

**狀態**: 🟡 活躍開發中 (Phase 1)
**版本**: 19.0.1.0.0
**最後更新**: 2025-04-09

⭐ 如果這個專案對你有幫助，請給個 Star！
