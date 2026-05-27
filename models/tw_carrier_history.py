# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TwInvoiceCarrierHistory(models.Model):
    _name = 'tw.invoice.carrier.history'
    _description = '發票載具使用記錄'
    _order = 'invoice_date desc'

    invoice_id = fields.Many2one('account.move', string='發票', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='客戶', required=True, ondelete='cascade')

    carrier_type = fields.Selection([
        ('mobile_barcode', '手機條碼'),
        ('citizen_cert', '自然人憑證'),
        ('donation_code', '捐贈碼'),
    ], string='載具類型', required=True)

    carrier_num = fields.Char(string='載具號碼')
    invoice_date = fields.Date(string='發票日期', required=True, default=fields.Date.context_today)
    invoice_amount = fields.Float(string='發票金額', required=True)
    donation_unit = fields.Char(string='捐贈單位代碼')

    # Statistics
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        """Set company on create"""
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)
