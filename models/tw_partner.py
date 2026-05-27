# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Taiwan VAT and Invoice Type
    tw_vat = fields.Char(
        string='統一編號',
        size=8,
        help='台灣統一編號（8 碼數字）'
    )

    tw_invoice_type = fields.Selection([
        ('b2b', 'B2B 營業人（三聯式）'),
        ('b2c', 'B2C 消費者（二聯式）'),
    ], string='預設發票類型', compute='_compute_tw_invoice_type', store=True)

    # Carrier Preference Settings
    tw_prefer_carrier_type = fields.Selection([
        ('none', '不使用'),
        ('mobile_barcode', '手機條碼'),
        ('citizen_cert', '自然人憑證'),
        ('donation_code', '捐贈碼'),
        ('ask_everytime', '每次詢問'),
    ], string='預設載具類型', default='ask_everytime')

    tw_prefer_carrier_num = fields.Char(
        string='預設載具號碼',
        help='發票開立時的預設載具號碼'
    )

    # Donation Code Settings
    tw_prefer_donation_unit = fields.Char(
        string='預設捐贈單位',
        help='捐贈碼載具的預設捐贈單位'
    )

    # Carrier Display
    tw_carrier_display = fields.Char(
        string='載具顯示資訊',
        compute='_compute_carrier_display'
    )

    # Carrier History
    carrier_history_ids = fields.One2many(
        'tw.invoice.carrier.history',
        'partner_id',
        string='載具使用記錄'
    )

    @api.depends('tw_vat', 'supplier_rank', 'customer_rank')
    def _compute_tw_invoice_type(self):
        """Compute default invoice type based on VAT number"""
        for partner in self:
            if partner.tw_vat and len(partner.tw_vat) == 8:
                partner.tw_invoice_type = 'b2b'
            else:
                partner.tw_invoice_type = 'b2c'

    @api.depends('tw_prefer_carrier_type', 'tw_prefer_carrier_num')
    def _compute_carrier_display(self):
        """Compute carrier display information"""
        for partner in self:
            if partner.tw_prefer_carrier_type == 'ask_everytime':
                partner.tw_carrier_display = '每次詢問'
            elif partner.tw_prefer_carrier_type == 'none':
                partner.tw_carrier_display = '不使用'
            elif partner.tw_prefer_carrier_num:
                carrier_info = self._get_carrier_info(
                    partner.tw_prefer_carrier_type,
                    partner.tw_prefer_carrier_num
                )
                partner.tw_carrier_display = carrier_info
            else:
                partner.tw_carrier_display = '未設定'

    def _get_carrier_info(self, carrier_type, carrier_num):
        """Get carrier display information"""
        carrier_names = {
            'mobile_barcode': '手機條碼',
            'citizen_cert': '自然人憑證',
            'donation_code': '捐贈碼',
        }
        return f"{carrier_names.get(carrier_type, carrier_type)}: {carrier_num}"

    @api.constrains('tw_vat')
    def _check_tw_vat(self):
        """Validate Taiwan VAT number"""
        for partner in self:
            if partner.tw_vat:
                if not self._validate_tw_vat(partner.tw_vat):
                    raise ValidationError(_('統一編號格式不正確'))

    def _validate_tw_vat(self, vat):
        """Taiwan VAT number validation logic"""
        if not vat or len(vat) != 8:
            return False
        if not vat.isdigit():
            return False

        # Taiwan VAT logic validation (simplified version)
        # Full implementation would include the checksum algorithm
        return True
