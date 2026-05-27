# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError
from datetime import date


@tagged('post_install', '-at_install')
class TestPartner(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner']

    def test_01_create_partner_with_vat(self):
        """Test creating partner with Taiwan VAT (8-digit B2B)"""
        partner = self.partner.create({
            'name': 'Test Company',
            'tw_vat': '12345678',
            'is_company': True,
        })
        self.assertEqual(partner.tw_vat, '12345678')
        self.assertEqual(partner.tw_invoice_type, 'b2b')

    def test_02_partner_without_vat(self):
        """Test partner without VAT is B2C"""
        partner = self.partner.create({
            'name': 'Test Individual',
            'tw_vat': False,
        })
        self.assertEqual(partner.tw_invoice_type, 'b2c')

    def test_03_partner_invalid_vat(self):
        """Test invalid VAT format raises error"""
        with self.assertRaises(ValidationError):
            self.partner.create({
                'name': 'Bad VAT',
                'tw_vat': '123',
            })

    def test_04_partner_vat_not_numeric(self):
        """Test non-numeric VAT raises error"""
        with self.assertRaises(ValidationError):
            self.partner.create({
                'name': 'Bad VAT',
                'tw_vat': 'ABCDEFGH',
            })

    def test_05_partner_carrier_preference(self):
        """Test partner carrier preference fields"""
        partner = self.partner.create({
            'name': 'Carrier Test',
            'tw_prefer_carrier_type': 'mobile_barcode',
            'tw_prefer_carrier_num': '/AB12345',
        })
        self.assertEqual(partner.tw_prefer_carrier_type, 'mobile_barcode')


@tagged('post_install', '-at_install')
class TestInvoice(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.invoice_model = self.env['account.move']
        self.partner_b2b = self.env['res.partner'].create({
            'name': 'B2B Company',
            'tw_vat': '12345678',
            'is_company': True,
        })
        self.partner_b2c = self.env['res.partner'].create({
            'name': 'B2C Individual',
        })
        # Get sales journal
        self.sales_journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
        ], limit=1)
        # Get income account
        self.income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
        ], limit=1)
        if not self.income_account:
            self.income_account = self.env['account.account'].search([], limit=1)

    def test_01_invoice_type_b2b(self):
        """Test B2B invoice type auto-detection"""
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        invoice = self.invoice_model.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2b.id,
            'invoice_date': date.today(),
            'journal_id': self.sales_journal.id,
            'tw_buyer_vat': self.partner_b2b.tw_vat,
        })
        self.assertEqual(invoice.tw_invoice_type, 'tw_triple')

    def test_02_invoice_type_b2c(self):
        """Test B2C invoice type auto-detection"""
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        invoice = self.invoice_model.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2c.id,
            'invoice_date': date.today(),
            'journal_id': self.sales_journal.id,
        })
        self.assertEqual(invoice.tw_invoice_type, 'tw_double')

    def test_03_invoice_carrier_fields(self):
        """Test invoice carrier field availability"""
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        invoice = self.invoice_model.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2c.id,
            'invoice_date': date.today(),
            'journal_id': self.sales_journal.id,
        })
        self.assertTrue(hasattr(invoice, 'tw_carrier_type'))
        self.assertTrue(hasattr(invoice, 'tw_carrier_num'))
        self.assertTrue(hasattr(invoice, 'tw_tax_type'))


@tagged('post_install', '-at_install')
class TestInvoiceSequence(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.period_model = self.env['tw.invoice.period']
        self.sequence_model = self.env['tw.invoice.sequence']
        self.sales_journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)

    def _create_period(self, **kwargs):
        defaults = {
            'name': 'Test Period 2026-01',
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 2, 28),
        }
        defaults.update(kwargs)
        return self.period_model.create(defaults)

    def _create_sequence(self, period, **kwargs):
        if not self.sales_journal:
            self.skipTest('No sales journal found')
        defaults = {
            'name': f"{kwargs.get('prefix', 'AB')} Track",
            'prefix': 'AB',
            'period_id': period.id,
            'start_number': 1,
            'end_number': 100,
            'journal_id': self.sales_journal.id,
        }
        defaults.update(kwargs)
        return self.sequence_model.create(defaults)

    def test_01_create_period(self):
        """Test creating an invoice period"""
        period = self._create_period()
        self.assertEqual(period.name, 'Test Period 2026-01')
        self.assertFalse(period.is_closed)

    def test_02_create_sequence(self):
        """Test creating an invoice sequence"""
        period = self._create_period()
        sequence = self._create_sequence(period, prefix='AB')
        self.assertEqual(sequence.prefix, 'AB')
        self.assertFalse(sequence.is_exhausted)

    def test_03_get_next_invoice_number(self):
        """Test getting next invoice number"""
        period = self._create_period()
        sequence = self._create_sequence(period, prefix='AB')
        number = sequence.get_next_invoice_number()
        self.assertTrue(number)
        self.assertIn('AB', number)

    def test_04_sequence_exhausted(self):
        """Test sequence exhaustion detection"""
        period = self._create_period()
        sequence = self._create_sequence(period, prefix='ZZ', end_number=2)
        sequence.get_next_invoice_number()
        sequence.get_next_invoice_number()
        self.assertTrue(sequence.is_exhausted)


@tagged('post_install', '-at_install')
class TestAccountAccount(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.account_model = self.env['account.account']

    def test_01_tw_account_fields_exist(self):
        """Test that Taiwan account fields exist on account.account"""
        account = self.account_model.search([], limit=1)
        self.assertTrue(hasattr(account, 'tw_account_code'))
        self.assertTrue(hasattr(account, 'tw_account_type'))
        self.assertTrue(hasattr(account, 'tw_tax_deductible'))
        self.assertTrue(hasattr(account, 'tw_account_group'))

    def test_02_tw_account_code_validation(self):
        """Test Taiwan account code validation (7 digits)"""
        # Valid 7-digit code should work
        account = self.account_model.create({
            'name': 'Test TW Account',
            'code': '9990001',
            'account_type': 'asset_cash',
            'tw_account_code': '9990001',
            'tw_account_type': 'asset',
        })
        self.assertEqual(account.tw_account_code, '9990001')

    def test_03_account_name_get(self):
        """Test account name_get includes Taiwan code"""
        account = self.account_model.create({
            'name': 'Test Account NameGet',
            'code': '9990002',
            'account_type': 'asset_cash',
            'tw_account_code': '9990002',
        })
        display_name = account.name_get()[0][1]
        self.assertIn('9990002', display_name)
