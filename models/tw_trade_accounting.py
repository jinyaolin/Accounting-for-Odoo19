# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TwTradeAccounting(models.Model):
    _name = 'tw.trade.accounting'
    _description = 'Taiwan Trade Accounting Management'

    # Foreign currency revaluation
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    @api.model
    def revalue_foreign_currency(self):
        """Revalue foreign currency accounts"""
        # Get all foreign currency move lines
        move_lines = self.env['account.move.line'].search([
            ('parent_state', '=', 'posted'),
            ('amount_currency', '!=', 0.0),
            ('currency_id', '!=', self.env.company.currency_id),
        ])

        revaluated_lines = []
        total_gain_loss = 0.0

        for line in move_lines:
            # Calculate unrealized gain/loss
            old_rate = line.foreign_currency_rate if hasattr(line, 'foreign_currency_rate') else 1.0
            current_rate = self._get_current_rate(line.currency_id)

            if old_rate != current_rate:
                # Calculate revaluation amount
                amount_currency = line.amount_currency
                old_amount_tcy = amount_currency * old_rate
                new_amount_tcy = amount_currency * current_rate

                gain_loss = new_amount_tcy - old_amount_tcy
                total_gain_loss += gain_loss

                # Create revaluation journal entry
                self._create_revaluation_entry(line, gain_loss, current_rate)
                revaluated_lines.append(line.id)

        return {
            'revalued_count': len(revaluated_lines),
            'total_gain_loss': total_gain_loss,
        }

    def _get_current_rate(self, currency_id):
        """Get current exchange rate"""
        # Implementation would fetch from currency rates
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency_id.id),
            ('company_id', '=', self.env.company.id),
        ], order='name desc', limit=1)

        if rate:
            return rate.rate
        else:
            return 1.0

    def _create_revaluation_entry(self, move_line, gain_loss, new_rate):
        """Create revaluation journal entry"""
        # Implementation would create accounting entry for currency revaluation
        pass

    # Customs duty processing
    @api.model
    def calculate_customs_duty(self, import_move_id):
        """Calculate customs duty for import move"""
        move = self.env['stock.move'].browse(import_move_id)

        if move.picking_type_id.code != 'incoming':
            return

        # Calculate duty based on HS code and value
        total_value = sum(move.move_line_ids.mapped('price_unit'))
        duty_rate = self._get_customs_duty_rate(move)

        customs_duty = total_value * duty_rate

        # Create accounting entry
        self._create_customs_entry(move, customs_duty)

        return {
            'total_value': total_value,
            'duty_rate': duty_rate,
            'customs_duty': customs_duty,
        }

    def _get_customs_duty_rate(self, move):
        """Get customs duty rate based on product"""
        # Implementation would fetch from customs tariff table
        # based on product HS code
        return 0.0  # Default duty rate

    def _create_customs_entry(self, move, customs_duty):
        """Create customs duty accounting entry"""
        # Implementation would create journal entry for customs duty
        pass

    # Freight and insurance distribution
    @api.model
    def distribute_freight_insurance(self, picking_id):
        """Distribute freight and insurance costs to goods received"""
        picking = self.env['stock.picking'].browse(picking_id)

        total_freight = picking.total_freight or 0.0
        total_insurance = picking.total_insurance or 0.0
        total_cost = total_freight + total_insurance

        if total_cost == 0:
            return

        # Get total value of received goods
        total_value = sum(picking.move_lines_without_package.mapped('value'))
        if total_value == 0:
            return

        # Distribute costs proportionally
        for move_line in picking.move_lines_without_package:
            if move_line.value:
                ratio = move_line.value / total_value
                allocated_cost = total_cost * ratio

                # Update product cost
                move_line.product_id.standard_price += (allocated_cost / move_line.product_qty)

        return {
            'distributed_cost': total_cost,
            'lines_updated': len(picking.move_lines_without_package),
        }

    # Export zero-tax refund processing
    @api.model
    def calculate_export_refund(self, invoice_id):
        """Calculate export zero-tax refund"""
        invoice = self.env['account.move'].browse(invoice_id)

        if invoice.move_type != 'out_invoice':
            raise ValidationError(_('Only customer invoices can have export refund'))

        # Check if invoice has export proof
        # Implementation would check for export documents
        refund_amount = 0.0

        for line in invoice.invoice_line_ids:
            if line.tax_line_id.tw_tax_type == 'vat_zero':
                # Calculate refundable input tax portion
                # This is simplified logic
                pass

        return {
            'invoice_id': invoice.id,
            'refund_amount': refund_amount,
        }
