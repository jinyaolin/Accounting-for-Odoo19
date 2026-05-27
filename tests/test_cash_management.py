# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError
from datetime import date


@tagged('post_install', '-at_install')
class TestCashReceipt(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.cash_receipt = self.env['tw.cash.receipt']
        self.cash_journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        # Get a revenue account for testing
        self.revenue_account = self.env['account.account'].search([
            ('account_type', '=', 'income_other'),
        ], limit=1)
        if not self.revenue_account:
            self.revenue_account = self.env['account.account'].search([], limit=1)

    def test_01_create_receipt(self):
        """Test creating a cash receipt with auto sequence"""
        receipt = self.cash_receipt.create({
            'date': date.today(),
            'receipt_type': 'sales',
            'amount': 5000.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'cash',
        })
        self.assertTrue(receipt.name)
        self.assertNotEqual(receipt.name, 'New')
        self.assertEqual(receipt.state, 'draft')
        self.assertEqual(receipt.amount, 5000.0)

    def test_02_receipt_state_flow(self):
        """Test receipt state transitions: draft -> confirmed -> posted"""
        receipt = self.cash_receipt.create({
            'date': date.today(),
            'receipt_type': 'sales',
            'amount': 1000.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'cash',
        })
        self.assertEqual(receipt.state, 'draft')

        # Draft -> Confirmed
        receipt.action_confirm()
        self.assertEqual(receipt.state, 'confirmed')

        # Confirmed -> Posted (only if cash journal exists)
        if self.cash_journal:
            receipt.action_post()
            self.assertEqual(receipt.state, 'posted')
            self.assertTrue(receipt.move_id)
        else:
            with self.assertRaises(Exception):
                receipt.action_post()

    def test_03_receipt_cancel_and_reset(self):
        """Test receipt cancel and reset to draft"""
        receipt = self.cash_receipt.create({
            'date': date.today(),
            'receipt_type': 'other',
            'amount': 500.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'cash',
        })
        receipt.action_cancel()
        self.assertEqual(receipt.state, 'cancelled')

        receipt.action_draft()
        self.assertEqual(receipt.state, 'draft')

    def test_04_receipt_cash_limit_constraint(self):
        """Test cash transaction limit (100,000 TWD)"""
        with self.assertRaises(ValidationError):
            self.cash_receipt.create({
                'date': date.today(),
                'receipt_type': 'sales',
                'amount': 150000.0,
                'account_id': self.revenue_account.id,
                'payment_method': 'cash',
            })

    def test_05_receipt_transfer_no_limit(self):
        """Test transfer payment has no cash limit"""
        receipt = self.cash_receipt.create({
            'date': date.today(),
            'receipt_type': 'sales',
            'amount': 200000.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'transfer',
        })
        self.assertEqual(receipt.amount, 200000.0)

    def test_06_receipt_currency_default(self):
        """Test currency defaults to company currency"""
        receipt = self.cash_receipt.create({
            'date': date.today(),
            'receipt_type': 'sales',
            'amount': 1000.0,
            'account_id': self.revenue_account.id,
            'payment_method': 'cash',
        })
        self.assertEqual(receipt.currency_id, self.env.company.currency_id)


@tagged('post_install', '-at_install')
class TestCashPayment(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.cash_payment = self.env['tw.cash.payment']
        self.cash_journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        self.expense_account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
        ], limit=1)
        if not self.expense_account:
            self.expense_account = self.env['account.account'].search([], limit=1)

    def test_01_create_payment(self):
        """Test creating a cash payment with auto sequence"""
        payment = self.cash_payment.create({
            'date': date.today(),
            'payment_type': 'expense',
            'amount': 3000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'cash',
        })
        self.assertTrue(payment.name)
        self.assertNotEqual(payment.name, 'New')
        self.assertEqual(payment.state, 'draft')
        self.assertEqual(payment.amount, 3000.0)

    def test_02_payment_state_flow(self):
        """Test payment state transitions: draft -> submitted -> approved -> posted"""
        payment = self.cash_payment.create({
            'date': date.today(),
            'payment_type': 'expense',
            'amount': 2000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'cash',
        })
        self.assertEqual(payment.state, 'draft')

        # Draft -> Submitted
        payment.action_submit()
        self.assertEqual(payment.state, 'submitted')

        # Submitted -> Approved
        payment.action_approve()
        self.assertEqual(payment.state, 'approved')
        self.assertTrue(payment.approved_by)
        self.assertTrue(payment.approval_date)

        # Approved -> Posted
        if self.cash_journal:
            payment.action_post()
            self.assertEqual(payment.state, 'posted')
            self.assertTrue(payment.move_id)
        else:
            with self.assertRaises(Exception):
                payment.action_post()

    def test_03_payment_post_without_approve(self):
        """Test posting without approval should fail"""
        payment = self.cash_payment.create({
            'date': date.today(),
            'payment_type': 'expense',
            'amount': 1000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'cash',
        })
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_04_payment_cancel_and_reset(self):
        """Test payment cancel and reset to draft"""
        payment = self.cash_payment.create({
            'date': date.today(),
            'payment_type': 'other',
            'amount': 500.0,
            'account_id': self.expense_account.id,
            'payment_method': 'cash',
        })
        payment.action_cancel()
        self.assertEqual(payment.state, 'cancelled')

        payment.action_draft()
        self.assertEqual(payment.state, 'draft')

    def test_05_payment_cash_limit_constraint(self):
        """Test cash transaction limit (100,000 TWD)"""
        with self.assertRaises(ValidationError):
            self.cash_payment.create({
                'date': date.today(),
                'payment_type': 'purchase',
                'amount': 150000.0,
                'account_id': self.expense_account.id,
                'payment_method': 'cash',
            })

    def test_06_payment_transfer_no_limit(self):
        """Test transfer payment has no cash limit"""
        payment = self.cash_payment.create({
            'date': date.today(),
            'payment_type': 'purchase',
            'amount': 200000.0,
            'account_id': self.expense_account.id,
            'payment_method': 'transfer',
        })
        self.assertEqual(payment.amount, 200000.0)


@tagged('post_install', '-at_install')
class TestCashJournal(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.cash_journal_model = self.env['tw.cash.journal']

    def test_01_create_journal(self):
        """Test creating a cash journal"""
        journal = self.cash_journal_model.create({
            'date': date.today(),
            'opening_balance': 10000.0,
        })
        self.assertEqual(journal.state, 'draft')
        self.assertEqual(journal.opening_balance, 10000.0)

    def test_02_journal_closing_balance(self):
        """Test closing balance calculation"""
        journal = self.cash_journal_model.create({
            'date': date(2020, 1, 1),
            'opening_balance': 5000.0,
        })
        # No posted receipts/payments for this date, should be opening_balance
        self.assertEqual(journal.closing_balance, 5000.0)

    def test_03_journal_confirm(self):
        """Test journal confirmation"""
        journal = self.cash_journal_model.create({
            'date': date(2020, 1, 2),
            'opening_balance': 1000.0,
        })
        journal.action_confirm()
        self.assertEqual(journal.state, 'confirmed')

        journal.action_draft()
        self.assertEqual(journal.state, 'draft')

    def test_04_journal_daily_report(self):
        """Test daily report generation"""
        journal = self.cash_journal_model.create({
            'date': date(2020, 1, 3),
            'opening_balance': 10000.0,
            'notes': 'Test notes',
        })
        report = journal.generate_daily_report()
        self.assertIn('現 金 日 報 表', report)
        self.assertIn('期初金額', report)
        self.assertIn('期末金額', report)
