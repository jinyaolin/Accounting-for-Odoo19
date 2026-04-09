# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    # Taiwan Chart of Accounts fields
    tw_account_code = fields.Char(
        string='Taiwan Account Code',
        help='Taiwan 7-digit account code according to Chart of Accounts standards'
    )

    tw_account_type = fields.Selection([
        ('asset', 'Assets (資產)'),
        ('liability', 'Liabilities (負債)'),
        ('equity', 'Equity (權益)'),
        ('revenue', 'Revenue (收入)'),
        ('expense', 'Expense (費用)'),
    ], string='Taiwan Account Type')

    tw_tax_deductible = fields.Boolean(
        string='Tax Deductible',
        help='Whether this account can be used for tax deduction'
    )

    tw_account_group = fields.Char(
        string='Account Group',
        help='Taiwan account group for financial statement classification'
    )

    @api.constrains('tw_account_code')
    def _check_tw_account_code(self):
        """Validate Taiwan account code format"""
        for account in self:
            if account.tw_account_code:
                if not account.tw_account_code.isdigit():
                    raise ValidationError(_('Taiwan account code must contain only digits'))
                if len(account.tw_account_code) != 7:
                    raise ValidationError(_('Taiwan account code must be 7 digits'))

    def name_get(self):
        """Override to include Taiwan account code"""
        result = []
        for account in self:
            name = account.name
            if account.tw_account_code:
                name = f"[{account.tw_account_code}] {name}"
            result.append((account.id, name))
        return result
