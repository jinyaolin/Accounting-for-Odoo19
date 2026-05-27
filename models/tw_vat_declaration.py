# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io


class TwVATMediaDeclaration(models.Model):
    _name = 'tw.vat.media.declaration'
    _description = '加值稅申報'

    name = fields.Char(string='申報名稱', required=True)
    declaration_type = fields.Selection([
        ('401', '401 - 銷售額與輸出稅額'),
        ('403', '403 - 採購額與輸入稅額'),
        ('405', '405 - 退匯資料'),
    ], string='申報類型', required=True)

    # Period
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    # Tax amounts
    total_sales = fields.Float(string='銷售總額', default=0.0)
    total_taxable_sales = fields.Float(string='應稅銷售額', default=0.0)
    total_exempt_sales = fields.Float(string='免稅銷售額', default=0.0)
    total_zero_sales = fields.Float(string='零稅率銷售額', default=0.0)

    total_output_tax = fields.Float(string='輸出稅額總計', default=0.0)
    total_input_tax = fields.Float(string='輸入稅額總計', default=0.0)

    # Calculated fields
    net_tax_payable = fields.Float(
        string='淨應納稅額/(退稅額)',
        compute='_compute_net_tax',
        store=True
    )

    # Declaration file
    declaration_file = fields.Binary(string='申報檔案 (TXT)')
    declaration_filename = fields.Char(string='檔案名稱')

    # Status
    state = fields.Selection([
        ('draft', '草稿'),
        ('calculated', '已計算'),
        ('file_generated', '檔案已產生'),
        ('submitted', '已申報'),
    ], string='狀態', default='draft')

    @api.depends('total_output_tax', 'total_input_tax')
    def _compute_net_tax(self):
        """Calculate net tax payable or refundable"""
        for declaration in self:
            declaration.net_tax_payable = (
                declaration.total_output_tax - declaration.total_input_tax
            )

    def calculate_declaration(self):
        """Calculate declaration from invoices"""
        self.ensure_one()

        # Get all invoices in period
        invoices = self.env['account.move'].search([
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
            ('date', '>=', self.period_start),
            ('date', '<=', self.period_end),
            ('state', '=', 'posted'),
        ])

        # Calculate totals
        for invoice in invoices:
            if invoice.move_type in ['out_invoice', 'out_refund']:
                self.total_sales += invoice.amount_untaxed
                # Add tax based on type
                for line in invoice.line_ids:
                    if line.tax_line_id:
                        if line.tax_line_id.tw_tax_type == 'vat_5':
                            self.total_taxable_sales += line.price_subtotal
                            self.total_output_tax += line.price_total - line.price_subtotal
                        elif line.tax_line_id.tw_tax_type == 'vat_zero':
                            self.total_zero_sales += line.price_subtotal
                        elif line.tax_line_id.tw_tax_type == 'vat_exempt':
                            self.total_exempt_sales += line.price_subtotal

            elif invoice.move_type in ['in_invoice', 'in_refund']:
                # Input tax calculation
                for line in invoice.line_ids:
                    if line.tax_line_id and line.tax_line_id.tw_tax_type == 'vat_5':
                        self.total_input_tax += line.price_total - line.price_subtotal

        self.state = 'calculated'

    def generate_declaration_file(self):
        """Generate media declaration TXT file"""
        self.ensure_one()

        if self.state != 'calculated':
            raise ValidationError(_('Please calculate declaration first'))

        lines = []

        # Header record
        lines.append(self._generate_header_record())

        # Data records
        if self.declaration_type == '401':
            lines.extend(self._generate_401_records())
        elif self.declaration_type == '403':
            lines.extend(self._generate_403_records())
        elif self.declaration_type == '405':
            lines.extend(self._generate_405_records())

        # Footer record
        lines.append(self._generate_footer_record())

        # Generate file content
        file_content = '\r\n'.join(lines) + '\r\n'

        # Create binary file
        self.declaration_file = base64.b64encode(file_content.encode('utf-8'))
        self.declaration_filename = '%s_%s.txt' % (
            self.declaration_type,
            self.period_start.strftime('%Y%m%d')
        )
        self.state = 'file_generated'

        return {
            'type': 'binary',
            'filename': self.declaration_filename,
            'data': self.declaration_file,
        }

    def _generate_header_record(self):
        """Generate header record"""
        return '%s%s%s' % (
            '401',  # Record type
            self.period_start.strftime('%Y%m%d'),  # Period
            '00000',  # Reserved
        )

    def _generate_401_records(self):
        """Generate 401 declaration records"""
        records = []
        # Implementation would generate sales records
        return records

    def _generate_403_records(self):
        """Generate 403 declaration records"""
        records = []
        # Implementation would generate purchase records
        return records

    def _generate_405_records(self):
        """Generate 405 refund records"""
        records = []
        # Implementation would generate refund records
        return records

    def _generate_footer_record(self):
        """Generate footer record"""
        return '99999999999'

    def action_download_file(self):
        """Download declaration file"""
        self.ensure_one()

        if not self.declaration_file:
            self.generate_declaration_file()

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s?download=true' % (
                self._name,
                self.id
            ),
            'target': 'new',
        }


class TwVATDeclarationReport(models.TransientModel):
    _name = 'tw.vat.declaration.report'
    _description = 'Taiwan VAT Declaration Report'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    declaration_type = fields.Selection([
        ('401', '401 - Sales & Output VAT'),
        ('403', '403 - Purchases & Input VAT'),
    ], string='Declaration Type', required=True, default='401')

    def generate_report(self):
        """Generate declaration report"""
        self.ensure_one()

        # Create or update declaration
        declaration = self.env['tw.vat.media.declaration'].create({
            'name': '%s Declaration %s to %s' % (
                self.declaration_type,
                self.date_from,
                self.date_to
            ),
            'declaration_type': self.declaration_type,
            'period_start': self.date_from,
            'period_end': self.date_to,
        })

        declaration.calculate_declaration()

        return {
            'type': 'ir.actions.act_window',
            'name': 'VAT Declaration',
            'res_model': 'tw.vat.media.declaration',
            'res_id': declaration.id,
            'view_mode': 'form',
            'target': 'new',
        }
