# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class TwCashJournal(models.Model):
    _name = 'tw.cash.journal'
    _description = '現金日記帳'
    _order = 'date desc, id desc'
    _rec_name = 'date'

    # Date
    date = fields.Date(string='日期', required=True, default=fields.Date.context_today)

    # Opening balance
    opening_balance = fields.Float(string='期初金額', required=True, digits='Account', default=0.0)

    # Cash receipts (inflows) - computed from related records
    total_receipts = fields.Float(string='收入合計', compute='_compute_totals', store=True, digits='Account')

    # Cash payments (outflows) - computed from related records
    total_payments = fields.Float(string='支出合計', compute='_compute_totals', store=True, digits='Account')

    # Balance
    closing_balance = fields.Float(string='期末金額', compute='_compute_totals', store=True, digits='Account')

    # Bank accounts
    bank_balance = fields.Float(string='銀行存款餘額', compute='_compute_bank_balance', digits='Account')

    # Notes
    notes = fields.Text(string='備註說明')

    # Status
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已確認'),
    ], string='狀態', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='公司', required=True, default=lambda self: self.env.company)

    @api.depends('opening_balance', 'date')
    def _compute_totals(self):
        """Calculate total receipts, payments and closing balance for the date"""
        for journal in self:
            # Get receipts for this date
            receipts = self.env['tw.cash.receipt'].search([
                ('date', '=', journal.date),
                ('state', '=', 'posted'),
                ('company_id', '=', journal.company_id.id)
            ])
            journal.total_receipts = sum(receipt.amount for receipt in receipts)

            # Get payments for this date
            payments = self.env['tw.cash.payment'].search([
                ('date', '=', journal.date),
                ('state', '=', 'posted'),
                ('company_id', '=', journal.company_id.id)
            ])
            journal.total_payments = sum(payment.amount for payment in payments)

            journal.closing_balance = journal.opening_balance + journal.total_receipts - journal.total_payments

    def _compute_bank_balance(self):
        """Calculate bank balance from account balances"""
        for journal in self:
            # Get bank account balances
            bank_accounts = self.env['account.account'].search([
                ('company_ids', 'child_of', journal.company_id.id),
                ('tw_account_type', '=', 'asset'),
                ('account_type', 'like', 'asset_%')
            ])

            total_bank_balance = 0.0
            for account in bank_accounts:
                # Calculate balance from move lines
                move_lines = self.env['account.move.line'].search([
                    ('account_id', '=', account.id),
                    ('date', '<=', journal.date),
                    ('parent_state', '=', 'posted'),
                ])
                balance = sum(line.balance for line in move_lines)
                total_bank_balance += balance

            journal.bank_balance = total_bank_balance

    def action_confirm(self):
        """Confirm cash journal"""
        self.write({'state': 'confirmed'})

    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def generate_daily_report(self):
        """Generate daily cash report"""
        self.ensure_one()

        lines = []
        lines.append("============================================")
        lines.append("           現 金 日 報 表")
        lines.append("============================================")
        lines.append("")
        lines.append(f"日期：{self.date}")
        lines.append(f"公司：{self.company_id.name}")
        lines.append("")

        # Opening balance
        lines.append(f"{'期初金額：':20s} {self.opening_balance:>15.2f}")
        lines.append("")

        # Cash receipts
        lines.append("現金收入")
        lines.append("----------------------------------------")
        receipts = self.env['tw.cash.receipt'].search([
            ('date', '=', self.date),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ])
        for receipt in receipts:
            receipt_type = dict(receipt._fields['receipt_type'].get_description(self.env))[receipt.receipt_type]
            lines.append(f"  {receipt.name:10s} {receipt_type:15s} {receipt.amount:>15.2f}")
        lines.append(f"{'':20s} {'收入合計：':>15s} {self.total_receipts:>15.2f}")
        lines.append("")

        # Cash payments
        lines.append("現金支出")
        lines.append("----------------------------------------")
        payments = self.env['tw.cash.payment'].search([
            ('date', '=', self.date),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ])
        for payment in payments:
            payment_type = dict(payment._fields['payment_type'].get_description(self.env))[payment.payment_type]
            lines.append(f"  {payment.name:10s} {payment_type:15s} {payment.amount:>15.2f}")
        lines.append(f"{'':20s} {'支出合計：':>15s} {self.total_payments:>15.2f}")
        lines.append("")

        # Closing balance
        lines.append("============================================")
        lines.append(f"{'期末金額：':20s} {self.closing_balance:>15.2f}")
        lines.append(f"{'銀行存款：':20s} {self.bank_balance:>15.2f}")
        lines.append("============================================")

        if self.notes:
            lines.append("")
            lines.append("備註說明")
            lines.append("----------------------------------------")
            lines.append(self.notes)

        return '\n'.join(lines)

    @api.constrains('date')
    def _check_date_unique(self):
        """Ensure only one journal per date"""
        for journal in self:
            existing = self.search([
                ('date', '=', journal.date),
                ('company_id', '=', journal.company_id.id),
                ('id', '!=', journal.id)
            ])
            if existing:
                raise ValidationError(_('日期 {date} 的現金日記帳已經存在').format(date=journal.date))


class TwCashJournalReport(models.TransientModel):
    _name = 'tw.cash.journal.report'
    _description = '現金日報表向導'

    date_from = fields.Date(string='開始日期', required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string='結束日期', required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string='公司', required=True, default=lambda self: self.env.company)

    def generate_report(self):
        """Generate cash journal report for period"""
        self.ensure_one()

        # Create or update journals for dates in range
        journals = self.env['tw.cash.journal'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ], order='date asc')

        return {
            'type': 'ir.actions.act_window',
            'name': '現金日記帳',
            'res_model': 'tw.cash.journal',
            'view_mode': 'list,form',
            'domain': [('id', 'in', journals.ids)],
            'target': 'current',
        }