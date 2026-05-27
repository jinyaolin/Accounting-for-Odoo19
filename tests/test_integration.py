# -*- coding: utf-8 -*-
"""Integration tests for tw_accounting module - cross-model workflow tests."""
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError
from datetime import date


@tagged('post_install', '-at_install')
class TestCashReceiptFullWorkflow(common.TransactionCase):
    """Test complete cash receipt workflow with accounting entry validation."""

    def setUp(self):
        super().setUp()
        self.receipt_model = self.env['tw.cash.receipt']
        self.cash_journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        self.revenue_account = self.env['account.account'].search([
            ('account_type', '=', 'income_other'),
        ], limit=1) or self.env['account.account'].search([], limit=1)
        self.cash_account = self.env['account.account'].search([
            ('tw_account_code', '=', '1110001'),
        ], limit=1)

    def test_01_receipt_posting_creates_journal_entry(self):
        """Test: Receipt posting creates valid accounting entry with correct debit/credit."""
        if not self.cash_journal:
            self.skipTest('No cash journal found')
        receipt = self.receipt_model.create({
            'date': date.today(),
            'receipt_type': 'sales',
            'amount': 50000.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'cash',
        })

        # State: draft
        self.assertEqual(receipt.state, 'draft')
        self.assertFalse(receipt.move_id)

        # Confirm
        receipt.action_confirm()
        self.assertEqual(receipt.state, 'confirmed')

        # Post
        receipt.action_post()
        self.assertEqual(receipt.state, 'posted')

        # Verify accounting entry exists
        self.assertTrue(receipt.move_id)
        move = receipt.move_id
        self.assertEqual(move.journal_id.type, 'cash')

        # Verify debit + credit balance
        lines = move.line_ids
        total_debit = sum(line.debit for line in lines)
        total_credit = sum(line.credit for line in lines)
        self.assertEqual(total_debit, 50000.0)
        self.assertEqual(total_credit, 50000.0)
        self.assertEqual(total_debit, total_credit, "Debit must equal credit")

    def test_02_receipt_posting_with_asset_account(self):
        """Test: Receipt with asset account creates correct entry direction."""
        if not self.cash_journal:
            self.skipTest('No cash journal found')
        asset_account = self.env['account.account'].create({
            'name': 'Test Asset Account',
            'code': '9990003',
            'account_type': 'asset_current',
            'tw_account_code': '9990003',
            'tw_account_type': 'asset',
        })

        receipt = self.receipt_model.create({
            'date': date.today(),
            'receipt_type': 'other',
            'amount': 10000.0,
            'account_id': asset_account.id,
            'payment_method': 'transfer',
        })
        receipt.action_confirm()
        receipt.action_post()

        # For asset account: debit the account, credit cash
        move = receipt.move_id
        account_line = move.line_ids.filtered(lambda l: l.account_id == asset_account)
        self.assertTrue(account_line, "Should have a line for the asset account")
        self.assertEqual(account_line[0].debit, 10000.0)

    def test_03_receipt_currency_selection(self):
        """Test: Receipt can use different currencies."""
        company_currency = self.env.company.currency_id
        other_currencies = self.env['res.currency'].search([
            ('id', '!=', company_currency.id),
            ('active', '=', True),
        ], limit=1)

        receipt = self.receipt_model.create({
            'date': date.today(),
            'receipt_type': 'sales',
            'amount': 100.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'cash',
            'currency_id': other_currencies.id if other_currencies else company_currency.id,
        })
        if other_currencies:
            self.assertEqual(receipt.currency_id, other_currencies)
        else:
            self.assertEqual(receipt.currency_id, company_currency)


@tagged('post_install', '-at_install')
class TestCashPaymentFullWorkflow(common.TransactionCase):
    """Test complete cash payment workflow with approval and accounting entry validation."""

    def setUp(self):
        super().setUp()
        self.payment_model = self.env['tw.cash.payment']
        self.cash_journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        self.expense_account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
        ], limit=1) or self.env['account.account'].search([], limit=1)

    def test_01_payment_full_approval_workflow(self):
        """Test: Payment goes through draft → submitted → approved → posted."""
        if not self.cash_journal:
            self.skipTest('No cash journal found')
        payment = self.payment_model.create({
            'date': date.today(),
            'payment_type': 'expense',
            'amount': 25000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'cash',
        })

        # Draft state
        self.assertEqual(payment.state, 'draft')
        self.assertFalse(payment.approved_by)
        self.assertFalse(payment.move_id)

        # Submit
        payment.action_submit()
        self.assertEqual(payment.state, 'submitted')

        # Approve
        payment.action_approve()
        self.assertEqual(payment.state, 'approved')
        self.assertEqual(payment.approved_by, self.env.user)
        self.assertTrue(payment.approval_date)

        # Post
        payment.action_post()
        self.assertEqual(payment.state, 'posted')
        self.assertTrue(payment.move_id)

        # Verify balanced entry
        move = payment.move_id
        total_debit = sum(line.debit for line in move.line_ids)
        total_credit = sum(line.credit for line in move.line_ids)
        self.assertEqual(total_debit, total_credit, "Debit must equal credit")

    def test_02_payment_cannot_post_without_approval(self):
        """Test: Payment in draft state cannot be posted directly."""
        payment = self.payment_model.create({
            'date': date.today(),
            'payment_type': 'expense',
            'amount': 5000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'cash',
        })
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_03_payment_approver_recorded(self):
        """Test: Approver user and date are recorded correctly."""
        payment = self.payment_model.create({
            'date': date.today(),
            'payment_type': 'purchase',
            'amount': 3000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'transfer',
        })
        payment.action_submit()
        payment.action_approve()

        self.assertEqual(payment.approved_by, self.env.user)
        self.assertEqual(payment.approval_date, date.today())


@tagged('post_install', '-at_install')
class TestCashJournalIntegration(common.TransactionCase):
    """Test cash journal with related receipts and payments."""

    def setUp(self):
        super().setUp()
        self.journal_model = self.env['tw.cash.journal']
        self.receipt_model = self.env['tw.cash.receipt']
        self.payment_model = self.env['tw.cash.payment']

    def test_01_journal_closing_balance_formula(self):
        """Test: closing_balance = opening_balance + total_receipts - total_payments."""
        journal = self.journal_model.create({
            'date': date(2020, 6, 15),
            'opening_balance': 50000.0,
        })
        # No posted receipts/payments for this old date
        self.assertEqual(journal.total_receipts, 0.0)
        self.assertEqual(journal.total_payments, 0.0)
        self.assertEqual(journal.closing_balance, 50000.0)

    def test_02_journal_daily_report_format(self):
        """Test: Daily report contains all required sections."""
        journal = self.journal_model.create({
            'date': date(2020, 7, 1),
            'opening_balance': 100000.0,
            'notes': 'Test integration notes',
        })
        report = journal.generate_daily_report()

        # Verify report structure
        self.assertIn('現 金 日 報 表', report)
        self.assertIn('期初金額', report)
        self.assertIn('現金收入', report)
        self.assertIn('現金支出', report)
        self.assertIn('期末金額', report)
        self.assertIn('銀行存款', report)
        self.assertIn('Test integration notes', report)

    def test_03_journal_date_uniqueness(self):
        """Test: Cannot create two journals for the same date and company."""
        self.journal_model.create({
            'date': date(2020, 8, 1),
            'opening_balance': 1000.0,
        })
        with self.assertRaises(Exception):
            self.journal_model.create({
                'date': date(2020, 8, 1),
                'opening_balance': 2000.0,
            })


@tagged('post_install', '-at_install')
class TestPartnerInvoiceIntegration(common.TransactionCase):
    """Test partner and invoice type auto-detection integration."""

    def setUp(self):
        super().setUp()
        self.partner_model = self.env['res.partner']
        self.invoice_model = self.env['account.move']
        self.sales_journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)

    def test_01_b2b_partner_creates_triple_invoice(self):
        """Test: Partner with VAT number → B2B triple invoice."""
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        partner = self.partner_model.create({
            'name': 'B2B Test Corp',
            'tw_vat': '12345678',
            'is_company': True,
        })

        invoice = self.invoice_model.create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': date.today(),
            'journal_id': self.sales_journal.id,
            'tw_buyer_vat': partner.tw_vat,
        })

        self.assertEqual(invoice.tw_invoice_type, 'tw_triple')

    def test_02_b2c_partner_creates_double_invoice(self):
        """Test: Partner without VAT number → B2C double invoice."""
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        partner = self.partner_model.create({
            'name': 'B2C Test Person',
        })

        invoice = self.invoice_model.create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': date.today(),
            'journal_id': self.sales_journal.id,
        })

        self.assertEqual(invoice.tw_invoice_type, 'tw_double')

    def test_03_partner_carrier_auto_fill_on_invoice(self):
        """Test: Partner carrier preferences auto-fill on invoice via onchange."""
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        partner = self.partner_model.create({
            'name': 'Carrier Test',
            'tw_prefer_carrier_type': 'mobile_barcode',
            'tw_prefer_carrier_num': '/AB12345',
        })

        invoice = self.invoice_model.new({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'journal_id': self.sales_journal.id,
        })
        # Trigger onchange to auto-fill carrier from partner
        invoice._onchange_partner_id()

        # Invoice should inherit carrier preferences from partner via onchange
        self.assertEqual(invoice.tw_carrier_type, 'mobile_barcode')

    def test_04_vat_validation_rejects_invalid(self):
        """Test: VAT validation rejects non-8-digit and non-numeric values."""
        with self.assertRaises(ValidationError):
            self.partner_model.create({'name': 'Bad', 'tw_vat': '123'})
        with self.assertRaises(ValidationError):
            self.partner_model.create({'name': 'Bad', 'tw_vat': 'ABCDEFGH'})
        with self.assertRaises(ValidationError):
            self.partner_model.create({'name': 'Bad', 'tw_vat': '1234567'})


@tagged('post_install', '-at_install')
class TestAccountAccountIntegration(common.TransactionCase):
    """Test Taiwan account code features."""

    def test_01_tw_account_code_in_name_get(self):
        """Test: Account name_get includes Taiwan account code."""
        account = self.env['account.account'].create({
            'name': 'Test NameGet Account',
            'code': '9990099',
            'account_type': 'asset_cash',
            'tw_account_code': '9990099',
        })
        display = account.name_get()[0]
        self.assertIn('9990099', display[1])

    def test_02_tw_account_search_by_type(self):
        """Test: Can search accounts by Taiwan account type."""
        account = self.env['account.account'].create({
            'name': 'Test Revenue Account',
            'code': '9990088',
            'account_type': 'income_other',
            'tw_account_type': 'revenue',
        })
        found = self.env['account.account'].search([
            ('tw_account_type', '=', 'revenue'),
            ('id', '=', account.id),
        ])
        self.assertEqual(len(found), 1)
        self.assertEqual(found.tw_account_type, 'revenue')
