# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Taiwan VAT and Invoice Type
    tw_vat = fields.Char(
        string='Taiwan VAT Number',
        size=8,
        help='Taiwan VAT Number (8 digits)'
    )

    tw_invoice_type = fields.Selection([
        ('b2b', 'B2B Business (Triple Copy)'),
        ('b2c', 'B2C Consumer (Double Copy)'),
    ], string='Default Invoice Type', compute='_compute_tw_invoice_type', store=True)

    # Carrier Preference Settings
    tw_prefer_carrier_type = fields.Selection([
        ('none', 'No Carrier'),
        ('mobile_barcode', 'Mobile Barcode'),
        ('citizen_cert', 'Citizen Digital Certificate'),
        ('donation_code', 'Donation Code'),
        ('ask_everytime', 'Ask Every Time'),
    ], string='Preferred Carrier Type', default='ask_everytime')

    tw_prefer_carrier_num = fields.Char(
        string='Preferred Carrier Number',
        help='Default carrier number for invoice issuance'
    )

    # Donation Code Settings
    tw_prefer_donation_unit = fields.Char(
        string='Preferred Donation Unit',
        help='Preferred donation unit code for donation code carrier'
    )

    # Carrier Display
    tw_carrier_display = fields.Char(
        string='Carrier Display Info',
        compute='_compute_carrier_display'
    )

    # Carrier History
    carrier_history_ids = fields.One2many(
        'tw.invoice.carrier.history',
        'partner_id',
        string='Carrier Usage History'
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
                partner.tw_carrier_display = 'Ask Every Time'
            elif partner.tw_prefer_carrier_type == 'none':
                partner.tw_carrier_display = 'No Carrier'
            elif partner.tw_prefer_carrier_num:
                carrier_info = self._get_carrier_info(
                    partner.tw_prefer_carrier_type,
                    partner.tw_prefer_carrier_num
                )
                partner.tw_carrier_display = carrier_info
            else:
                partner.tw_carrier_display = 'Not Set'

    def _get_carrier_info(self, carrier_type, carrier_num):
        """Get carrier display information"""
        carrier_names = {
            'mobile_barcode': 'Mobile Barcode',
            'citizen_cert': 'Citizen Certificate',
            'donation_code': 'Donation Code',
        }
        return f"{carrier_names.get(carrier_type, carrier_type)}: {carrier_num}"

    @api.constrains('tw_vat')
    def _check_tw_vat(self):
        """Validate Taiwan VAT number"""
        for partner in self:
            if partner.tw_vat:
                if not self._validate_tw_vat(partner.tw_vat):
                    raise ValidationError(_('Taiwan VAT number format is incorrect'))

    def _validate_tw_vat(self, vat):
        """Taiwan VAT number validation logic"""
        if not vat or len(vat) != 8:
            return False
        if not vat.isdigit():
            return False

        # Taiwan VAT logic validation (simplified version)
        # Full implementation would include the checksum algorithm
        return True
