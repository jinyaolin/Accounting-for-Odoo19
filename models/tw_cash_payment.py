# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TwCashPayment(models.Model):
    _name = 'tw.cash.payment'
    _description = '現金支出記錄'
    _order = 'date desc, id desc'

    name = fields.Char(string='支出單號', required=True, copy=False, readonly=True, default='New')

    # Basic information
    date = fields.Date(string='支出日期', required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='收款人')

    # Payment details
    payment_type = fields.Selection([
        ('purchase', '採購付款'),
        ('expense', '費用支出'),
        ('salary', '薪資支出'),
        ('tax', '稅捐支出'),
        ('dividend', '股利支出'),
        ('other', '其他支出'),
    ], string='支出類型', required=True, default='other')

    amount = fields.Float(string='支出金額', required=True, digits='Account')
    currency_id = fields.Many2one('res.currency', string='幣別', required=True,
        default=lambda self: self.env.company.currency_id)

    # Description
    description = fields.Text(string='說明')
    notes = fields.Text(string='備註')

    # Accounting integration
    move_id = fields.Many2one('account.move', string='會計分錄', readonly=True)
    account_id = fields.Many2one('account.account', string='會計科目', required=True,
        domain=[('tw_account_type', 'in', ['asset', 'expense', 'liability'])])

    # Payment method
    payment_method = fields.Selection([
        ('cash', '現金'),
        ('check', '支票'),
        ('transfer', '轉帳'),
    ], string='支付方式', required=True, default='cash')

    check_number = fields.Char(string='支票號碼')
    bank_id = fields.Many2one('res.bank', string='銀行')

    # Approval workflow
    approved_by = fields.Many2one('res.users', string='核准人', readonly=True)
    approval_date = fields.Date(string='核准日期', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('approved', '已核准'),
        ('posted', '已過帳'),
        ('cancelled', '已取消'),
    ], string='狀態', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='公司', required=True, default=lambda self: self.env.company)

    @api.model
    def create(self, vals_list):
        """Generate sequence number for new cash payment"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tw.cash.payment') or 'New'
        return super(TwCashPayment, self).create(vals_list)

    def action_submit(self):
        """Submit for approval"""
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Approve cash payment"""
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Date.context_today(self),
        })

    def action_post(self):
        """Post cash payment and create accounting entry"""
        self.ensure_one()

        if self.state not in ['approved']:
            raise ValidationError(_('請先核准支出單'))

        # Create accounting move
        move_vals = {
            'date': self.date,
            'journal_id': self.env['account.journal'].search([('type', '=', 'cash')], limit=1).id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_id.id,
                    'debit': self.amount if self.account_id.tw_account_type == 'asset' else 0,
                    'credit': self.amount if self.account_id.tw_account_type in ['expense', 'liability'] else 0,
                    'name': self.description or self.name,
                }),
                (0, 0, {
                    'account_id': self.env['account.account'].search([('tw_account_code', '=', '1110001'), ('company_ids', 'child_of', self.company_id.id)], limit=1).id or self.account_id.id,
                    'debit': self.amount if self.account_id.tw_account_type in ['expense', 'liability'] else 0,
                    'credit': self.amount if self.account_id.tw_account_type == 'asset' else 0,
                    'name': self.description or self.name,
                }),
            ],
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.write({
            'state': 'posted',
            'move_id': move.id
        })

    def action_cancel(self):
        """Cancel cash payment"""
        self.write({'state': 'cancelled'})

    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    @api.constrains('amount')
    def _check_amount(self):
        """Validate cash transaction limit (Taiwan regulation: 100,000 TWD)"""
        for payment in self:
            if payment.amount > 100000 and payment.payment_method == 'cash':
                raise ValidationError(_('根據台灣規定，現金交易不得超過100,000元'))