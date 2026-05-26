# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # Taiwan specific tax fields
    tw_tax_type = fields.Selection([
        ('vat_5', 'VAT 5%'),
        ('vat_zero', 'Zero Rate'),
        ('vat_exempt', 'Exempt'),
    ], string='Taiwan Tax Type')

    # Taiwan tax calculation rules
    tw_rounding_method = fields.Selection([
        ('round_half_up', 'Round Half Up'),
        ('five_six', 'Five Discard Six Round Up (五舍六入)'),
    ], string='Rounding Method', default='five_six')

    def compute_amount(self, base_amount, quantity=None, price_unit=None, product=None, partner=None, decimals=None):
        """Override to implement Taiwan 5/6 rounding rule"""
        if self.tw_tax_type and self.tw_rounding_method == 'five_six':
            # Taiwan specific 5/6 rounding
            amount = base_amount * self.amount
            # 五舍六入：小數點後第三位 >= 5 進位，否則捨去
            rounded_amount = (amount * 100) / 100
            # More precise 5/6 rounding logic
            import math
            if amount * 1000 % 10 >= 5:
                return math.ceil(amount * 100) / 100
            else:
                return math.floor(amount * 100) / 100

        return super().compute_amount(base_amount, quantity, price_unit, product, partner, decimals)
