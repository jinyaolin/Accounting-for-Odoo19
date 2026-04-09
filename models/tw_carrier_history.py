# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TwInvoiceCarrierHistory(models.Model):
    _name = 'tw.invoice.carrier.history'
    _description = 'Taiwan Invoice Carrier Usage History'
    _order = 'invoice_date desc'

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')

    carrier_type = fields.Selection([
        ('mobile_barcode', 'Mobile Barcode'),
        ('citizen_cert', 'Citizen Certificate'),
        ('donation_code', 'Donation Code'),
    ], string='Carrier Type', required=True)

    carrier_num = fields.Char(string='Carrier Number')
    invoice_date = fields.Date(string='Invoice Date', required=True, default=fields.Date.context_today)
    invoice_amount = fields.Float(string='Invoice Amount', required=True)
    donation_unit = fields.Char(string='Donation Unit Code')

    # Statistics
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        """Set company on create"""
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)
