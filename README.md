# Taiwan Accounting Localization for Odoo 19

完整的台灣會計本地化模組，符合台灣稅法和貿易公司需求。

## 🎯 核心功能

- ✅ 台灣會計科目系統
- ✅ 統一發票開立（二聯/三聯式）
- ✅ B2B/B2C 自動判斷機制
- ✅ 客戶預設載具設定
- ✅ 載具使用歷史記錄
- ✅ 愛心碼特殊處理
- ✅ 營業稅計算與申報準備

## 📦 模組結構

```
tw_accounting/
├── models/           # 資料模型
│   ├── account_account.py        # 會計科目擴展
│   ├── tw_partner.py              # 客戶/供應商擴展
│   ├── tw_invoice.py              # 發票擴展
│   ├── tw_carrier_history.py      # 載具使用歷史
│   └── tw_donation_unit.py        # 愛心碼捐贈單位
├── views/            # 視圖定義
├── security/         # 權限設定
└── data/            # 基礎資料
```

## 🚀 快速開始

### 安裝

```bash
# 將模組複製到 Odoo addons 目錄
cp -r tw_accounting /path/to/odoo/addons/

# 更新 Odoo 模組列表
./odoo-bin -c odoo.conf -d database -u all --stop-after-init

# 安裝模組
./odoo-bin -c odoo.conf -d database -i tw_accounting
```

### 使用

1. **設定客戶預設載具**
   - 進入客戶資料 → Taiwan Invoice Settings
   - 設定統一編號和預設載具

2. **開立統一發票**
   - 建立新發票時，系統自動判斷 B2B/B2C
   - 自動帶入客戶預設載具
   - 選擇愛心碼捐贈單位

3. **查看載具記錄**
   - 發票確認後自動記錄載具使用
   - 可查看載具使用歷史和統計

## 🎨 主要特色

### B2B/B2C 自動判斷

```python
# 有統編 → B2B 三聯式
# 無統編 → B2C 二聯式
```

### 載具預設設定

- 不使用載具
- 手機條碼 + 載具編號
- 自然人憑證 + 憑證號碼
- 愛心碼 + 捐贈單位
- 每次詢問

### 愛心碼特殊處理

- 必須選擇捐贈單位
- 自動顯示捐贈單位名稱
- 特殊列印格式
- 捐贈金額統計

## 📅 開發階段

- **Phase 1** (Week 1-4): 核心合規與發票開立 ✅ 進行中
- **Phase 2** (Week 5-8): 稅務申報與貿易特性
- **Phase 3** (Week 9-12): 進階功能與優化

## 🔧 技術架構

- 繼承 Odoo 核心模型
- 模組化設計
- 符合 Odoo 開發規範

## 📞 支援

- **GitHub**: https://github.com/jinyaolin
- **Email**: jinyao.lin@gmail.com

---

**狀態**: 🟡 開發中 (Phase 1)
