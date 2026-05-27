# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang


class TwFinancialReport(models.Model):
    _name = 'tw.financial.report'
    _description = '財務報表'

    name = fields.Char(string='報表名稱', required=True)
    report_type = fields.Selection([
        ('balance_sheet', '資產負債表'),
        ('income_statement', '損益表'),
        ('cash_flow', '現金流量表'),
        ('equity_change', '權益變動表'),
    ], string='報表類型', required=True)

    date_from = fields.Date(string='開始日期', required=True)
    date_to = fields.Date(string='結束日期', required=True)

    # Company information
    company_id = fields.Many2one('res.company', string='公司', required=True)

    # Taiwan specific format settings
    tw_format = fields.Selection([
        ('gaap', '台灣GAAP'),
        ('ifrs', 'IFRS'),
    ], string='報表格式', default='gaap')

    # Report data
    report_data = fields.Text(string='報表資料')
    report_file = fields.Binary(string='報表檔案 (PDF)')

    # Display settings
    hide_account_level = fields.Integer(string='隱藏深於此層級的科目', default=1)

    @api.model
    def generate_tw_balance_sheet(self):
        """Generate Taiwan format balance sheet"""
        self.ensure_one()

        # Get all accounts
        accounts = self.env['account.account'].search([
            ('company_ids', 'child_of', self.company_id.id),
        ])

        # Organize by Taiwan account classification
        balance_data = {
            'assets': self._get_account_balance(accounts, 'asset'),
            'liabilities': self._get_account_balance(accounts, 'liability'),
            'equity': self._get_account_balance(accounts, 'equity'),
        }

        # Calculate totals
        total_assets = balance_data['assets']['total']
        total_liabilities_equity = (
            balance_data['liabilities']['total'] +
            balance_data['equity']['total']
        )

        self.report_data = self._format_balance_sheet(balance_data, total_assets, total_liabilities_equity)

        return {
            'report_type': 'balance_sheet',
            'data': balance_data,
            'total_assets': total_assets,
            'total_liabilities_equity': total_liabilities_equity,
        }

    def _get_account_balance(self, accounts, account_type):
        """Get account balance by type"""
        tw_accounts = accounts.filtered(lambda a: a.tw_account_type == account_type)

        total = 0.0
        accounts_list = []

        for account in tw_accounts:
            balance = self._get_single_account_balance(account, self.date_from, self.date_to)
            total += balance

            if abs(balance) > 0.01:  # Only show significant amounts
                accounts_list.append({
                    'code': account.tw_account_code or account.code,
                    'name': account.name,
                    'balance': balance,
                })

        return {
            'accounts': accounts_list,
            'total': total,
        }

    def _get_single_account_balance(self, account, date_from, date_to):
        """Get account balance for period"""
        # Calculate balance from move lines
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('parent_state', '=', 'posted'),
        ])

        balance = sum(line.balance for line in move_lines)
        return balance

    def _format_balance_sheet(self, data, total_assets, total_liabilities_equity):
        """Format balance sheet for display"""
        lines = []

        lines.append("============================================")
        lines.append("           資 產 負 債 表")
        lines.append("============================================")
        lines.append("")
        lines.append(f"期間：{self.date_from} 至 {self.date_to}")
        lines.append("")

        # Assets section
        lines.append("資產")
        lines.append("----------------------------------------")
        for account in data['assets']['accounts']:
            lines.append(f"{account['code']:8s} {account['name']:30s} {account['balance']:>15.2f}")
        lines.append(f"{'':8s} {'資產總計':30s} {data['assets']['total']:>15.2f}")
        lines.append("")

        # Liabilities section
        lines.append("負債")
        lines.append("----------------------------------------")
        for account in data['liabilities']['accounts']:
            lines.append(f"{account['code']:8s} {account['name']:30s} {account['balance']:>15.2f}")
        lines.append(f"{'':8s} {'負債總計':30s} {data['liabilities']['total']:>15.2f}")
        lines.append("")

        # Equity section
        lines.append("權益")
        lines.append("----------------------------------------")
        for account in data['equity']['accounts']:
            lines.append(f"{account['code']:8s} {account['name']:30s} {account['balance']:>15.2f}")
        lines.append(f"{'':8s} {'權益總計':30s} {data['equity']['total']:>15.2f}")
        lines.append("")

        lines.append("============================================")
        lines.append(f"{'':8s} {'負債及權益總計':30s} {total_liabilities_equity:>15.2f}")
        lines.append("============================================")

        return '\n'.join(lines)

    @api.model
    def generate_tw_income_statement(self):
        """Generate Taiwan format income statement"""
        self.ensure_one()

        # Get revenue and expense accounts
        revenue_accounts = self.env['account.account'].search([
            ('company_ids', 'child_of', self.company_id.id),
            ('tw_account_type', 'in', ['revenue']),
        ])

        expense_accounts = self.env['account.account'].search([
            ('company_ids', 'child_of', self.company_id.id),
            ('tw_account_type', 'in', ['expense']),
        ])

        # Calculate balances
        total_revenue = 0.0
        total_expense = 0.0

        revenue_items = []
        expense_items = []

        for account in revenue_accounts:
            balance = self._get_single_account_balance(account, self.date_from, self.date_to)
            if abs(balance) > 0.01:
                total_revenue += balance
                revenue_items.append({
                    'code': account.tw_account_code or account.code,
                    'name': account.name,
                    'amount': balance,
                })

        for account in expense_accounts:
            balance = self._get_single_account_balance(account, self.date_from, self.date_to)
            if abs(balance) > 0.01:
                total_expense += abs(balance)
                expense_items.append({
                    'code': account.tw_account_code or account.code,
                    'name': account.name,
                    'amount': abs(balance),
                })

        # Calculate net income
        net_income = total_revenue - total_expense

        self.report_data = self._format_income_statement(
            revenue_items, expense_items, total_revenue, total_expense, net_income
        )

        return {
            'report_type': 'income_statement',
            'total_revenue': total_revenue,
            'total_expense': total_expense,
            'net_income': net_income,
        }

    def _format_income_statement(self, revenue_items, expense_items, total_revenue, total_expense, net_income):
        """Format income statement for display"""
        lines = []

        lines.append("============================================")
        lines.append("              損  盈  表")
        lines.append("============================================")
        lines.append("")
        lines.append(f"期間：{self.date_from} 至 {self.date_to}")
        lines.append("")

        # Revenue section
        lines.append("收入")
        lines.append("----------------------------------------")
        for item in revenue_items:
            lines.append(f"{item['code']:8s} {item['name']:30s} {item['amount']:>15.2f}")
        lines.append(f"{'':8s} {'收入總計':30s} {total_revenue:>15.2f}")
        lines.append("")

        # Expense section
        lines.append("費用")
        lines.append("----------------------------------------")
        for item in expense_items:
            lines.append(f"{item['code']:8s} {item['name']:30s} {item['amount']:>15.2f}")
        lines.append(f"{'':8s} {'費用總計':30s} {total_expense:>15.2f}")
        lines.append("")

        # Net income
        lines.append("============================================")
        net_text = "本期淨利" if net_income >= 0 else "本期淨損"
        lines.append(f"{'':8s} {net_text:30s} {net_income:>15.2f}")
        lines.append("============================================")

        return '\n'.join(lines)

    def action_print_report(self):
        """Print financial report"""
        self.ensure_one()

        if self.report_type == 'balance_sheet':
            result = self.generate_tw_balance_sheet()
        elif self.report_type == 'income_statement':
            result = self.generate_tw_income_statement()
        else:
            raise ValidationError(_('Report type not yet implemented'))

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=tw.financial.report&id=%s&filename=report.txt' % self.id,
            'target': 'new',
        }


class TwFinancialReportWizard(models.TransientModel):
    _name = 'tw.financial.report.wizard'
    _description = '財務報表向導'

    date_from = fields.Date(string='開始日期', required=True,
        default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string='結束日期', required=True,
        default=lambda self: fields.Date.context_today(self))

    report_type = fields.Selection([
        ('balance_sheet', '資產負債表'),
        ('income_statement', '損益表'),
        ('cash_flow', '現金流量表'),
        ('equity_change', '權益變動表'),
    ], string='報表類型', required=True, default='balance_sheet')

    def generate_report(self):
        """Generate selected financial report"""
        self.ensure_one()

        # Create report record
        report = self.env['tw.financial.report'].create({
            'name': '%s Report %s to %s' % (
                self.report_type,
                self.date_from,
                self.date_to
            ),
            'report_type': self.report_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.env.company.id,
        })

        # Generate report data
        if self.report_type == 'balance_sheet':
            result = report.generate_tw_balance_sheet()
        elif self.report_type == 'income_statement':
            result = report.generate_tw_income_statement()

        # Show result
        return {
            'type': 'ir.actions.act_window',
            'name': 'Financial Report',
            'res_model': 'tw.financial.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'new',
        }
