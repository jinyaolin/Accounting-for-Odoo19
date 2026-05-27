# -*- coding: utf-8 -*-

import urllib.request
import csv
import io
import logging
from datetime import date
from odoo import models, api, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

# Known currency codes from Taiwan Bank
_CURRENCY_CODES = {
    'USD', 'HKD', 'GBP', 'AUD', 'CAD', 'SGD', 'CHF', 'JPY', 'ZAR',
    'SEK', 'NZD', 'THB', 'PHP', 'IDR', 'EUR', 'KRW', 'VND', 'MYR',
    'CNY', 'HKD', 'MXN', 'ARS', 'BRL', 'INR', 'TWD',
}


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def action_update_tw_rates(self):
        """從台灣銀行抓取即期匯率並建立當日匯率記錄"""
        company_currency = self.env.company.currency_id

        url = 'https://rate.bot.com.tw/xrt/flcsv/0/day'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=15)
            content = response.read().decode('utf-8', errors='replace')
        except Exception as e:
            raise UserError(_('無法取得台灣銀行匯率資料: %s') % str(e))

        # 解析 CSV
        # CSV 結構 (22 欄):
        #   col 0: 幣別 (USD, HKD...)
        #   col 1-10: 本行買入 (現金, 即期, 遠期10/30/60/90/120/150/180天)
        #   col 11-20: 本行賣出 (現金, 即期, 遠期10/30/60/90/120/150/180天)
        #   即期匯率-本行賣出 = col 13
        tw_rates = {}
        for row in csv.reader(io.StringIO(content)):
            if not row:
                continue
            currency_code = row[0].strip().lstrip('\ufeff')  # Remove BOM
            if currency_code not in _CURRENCY_CODES:
                continue
            try:
                # 即期匯率-本行賣出（col 13）
                spot_selling = float(row[13].replace(',', ''))
                if spot_selling <= 0:
                    continue
                tw_rates[currency_code] = spot_selling
            except (ValueError, IndexError):
                continue

        if not tw_rates:
            raise UserError(_('無法解析台灣銀行匯率資料'))

        # 更新或建立匯率記錄
        today = date.today()
        rate_model = self.env['res.currency.rate']
        updated = []

        active_currencies = self.search([('active', '=', True)])
        for currency in active_currencies:
            if currency == company_currency:
                continue
            if currency.name not in tw_rates:
                continue

            # Odoo 匯率：rate = 1 單位外幣可兌換的公司幣別數量
            # 台灣銀行給的是 TWD/外幣，如果公司幣別是 TWD，直接使用
            rate_value = tw_rates[currency.name]

            existing = rate_model.search([
                ('currency_id', '=', currency.id),
                ('name', '=', today),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

            if existing:
                existing.rate = rate_value
            else:
                rate_model.create({
                    'currency_id': currency.id,
                    'name': today,
                    'rate': rate_value,
                    'company_id': self.env.company.id,
                })
            updated.append('%s: %.4f' % (currency.name, tw_rates[currency.name]))

        if not updated:
            raise UserError(_('沒有匹配的幣別可更新。請確認已啟用對應的幣別。'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('匯率更新完成'),
                'message': _('已更新 %d 種幣別：\n%s') % (len(updated), '\n'.join(updated)),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
