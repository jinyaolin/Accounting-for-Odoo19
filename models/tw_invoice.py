# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Taiwan Invoice Type (System auto-detection)
    tw_invoice_type = fields.Selection([
        ('tw_triple', 'Triple Copy (B2B)'),
        ('tw_double', 'Double Copy (B2C)'),
    ], string='Invoice Type', compute='_compute_tw_invoice_type', store=True)

    # Invoice Track and Number
    tw_invoice_track = fields.Char(
        string='Invoice Track',
        help='2-letter prefix for invoice number'
    )
    tw_invoice_number = fields.Char(
        string='Invoice Number',
        help='Full invoice number including track'
    )
    tw_invoice_period = fields.Char(
        string='Invoice Period',
        help='2-month period (e.g., 2024-01)'
    )

    # B2B Specific Fields
    tw_buyer_vat = fields.Char(
        string='Buyer VAT Number',
        size=8,
        help='Buyer VAT number (required for triple copy)'
    )
    tw_buyer_name = fields.Char(
        string='Buyer Name',
        help='Buyer company name'
    )

    # B2C Carrier Fields
    tw_carrier_type = fields.Selection([
        ('none', 'No Carrier'),
        ('mobile_barcode', 'Mobile Barcode'),
        ('citizen_cert', 'Citizen Certificate'),
        ('donation_code', 'Donation Code'),
    ], string='Carrier Type')

    tw_carrier_num = fields.Char(
        string='Carrier Number',
        help='Carrier number for VAT deduction'
    )

    # Donation Code Specific Fields
    tw_donation_unit = fields.Char(
        string='Donation Unit Code',
        size=7,
        help='Donation unit code (7 digits)'
    )

    tw_donation_unit_name = fields.Char(
        string='Donation Unit Name',
        compute='_compute_donation_unit_name'
    )

    # Carrier History
    tw_carrier_history_ids = fields.One2many(
        'tw.invoice.carrier.history',
        'invoice_id',
        string='Carrier Usage Records'
    )

    # Carrier Display
    tw_carrier_display = fields.Char(
        string='Carrier Display Info',
        compute='_compute_carrier_display'
    )

    # Tax Type
    tw_tax_type = fields.Selection([
        ('taxable', 'Taxable 5%'),
        ('zero', 'Zero Rate'),
        ('exempt', 'Exempt'),
    ], string='Tax Type', default='taxable')

    # Auto-detect invoice type
    @api.depends('partner_id', 'partner_id.tw_vat', 'move_type')
    def _compute_tw_invoice_type(self):
        """Auto-detect invoice type based on partner VAT"""
        for move in self:
            if move.move_type not in ['out_invoice', 'out_refund']:
                continue

            if move.partner_id and move.partner_id.tw_vat:
                # Has VAT → B2B Triple Copy
                move.tw_invoice_type = 'tw_triple'
            else:
                # No VAT → B2C Double Copy
                move.tw_invoice_type = 'tw_double'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Auto-fill carrier info when partner changes"""
        for move in self:
            if not move.partner_id:
                continue

            partner = move.partner_id

            # Handle carrier auto-fill based on partner preference
            if partner.tw_prefer_carrier_type == 'none':
                # Partner prefers no carrier
                move.tw_carrier_type = 'none'
                move.tw_carrier_num = False

            elif partner.tw_prefer_carrier_type == 'ask_everytime':
                # Ask every time, don't auto-fill
                move.tw_carrier_type = False
                move.tw_carrier_num = False

            elif partner.tw_prefer_carrier_type in ['mobile_barcode', 'citizen_cert', 'donation_code']:
                # Auto-fill preferred carrier
                move.tw_carrier_type = partner.tw_prefer_carrier_type
                move.tw_carrier_num = partner.tw_prefer_carrier_num

                # Donation code special handling
                if partner.tw_prefer_carrier_type == 'donation_code':
                    move.tw_donation_unit = partner.tw_prefer_donation_unit

    def _compute_carrier_display(self):
        """Compute carrier display information"""
        for move in self:
            if move.tw_invoice_type == 'tw_triple':
                # B2B Show VAT
                if move.tw_buyer_vat:
                    move.tw_carrier_display = f"VAT: {move.tw_buyer_vat}"
                else:
                    move.tw_carrier_display = 'VAT Required'

            elif move.tw_invoice_type == 'tw_double' and move.tw_carrier_type != 'none':
                # B2C Show carrier info
                carrier_info = self._get_carrier_display_info(move)
                move.tw_carrier_display = carrier_info

            else:
                move.tw_carrier_display = 'No Carrier'

    def _get_carrier_display_info(self, move):
        """Get carrier display information"""
        if move.tw_carrier_type == 'mobile_barcode':
            return f"Mobile Barcode: {move.tw_carrier_num}"

        elif move.tw_carrier_type == 'citizen_cert':
            # Mask middle part for privacy
            cert_num = move.tw_carrier_num
            if len(cert_num) == 16:
                masked = cert_num[:2] + '****' + cert_num[12:]
                return f"Citizen Cert: {masked}"
            return f"Citizen Cert: {cert_num}"

        elif move.tw_carrier_type == 'donation_code':
            # Show donation unit name
            return f"Donation Code: {move.tw_donation_unit_name or move.tw_donation_unit}"

        return 'Carrier Info'

    def _compute_donation_unit_name(self):
        """Lookup donation unit name"""
        for move in self:
            if move.tw_donation_unit:
                move.tw_donation_unit_name = self._lookup_donation_unit(
                    move.tw_donation_unit
                )
            else:
                move.tw_donation_unit_name = False

    def _lookup_donation_unit(self, unit_code):
        """Lookup donation unit name from registry"""
        # Implementation would query donation unit registry
        # For now, return placeholder
        unit = self.env['tw.donation.unit'].search([
            ('code', '=', unit_code)
        ], limit=1)
        return unit.name if unit else False

    @api.constrains('tw_invoice_type', 'tw_buyer_vat', 'tw_carrier_type', 'tw_carrier_num')
    def _check_tw_invoice_requirements(self):
        """Check invoice required fields"""
        for move in self:
            if move.move_type not in ['out_invoice', 'out_refund']:
                continue

            # B2B Triple Copy checks
            if move.tw_invoice_type == 'tw_triple':
                if not move.tw_buyer_vat or len(move.tw_buyer_vat) != 8:
                    raise ValidationError(_('Triple copy invoice must have buyer VAT number (8 digits)'))

                if not self._validate_tw_vat(move.tw_buyer_vat):
                    raise ValidationError(_('VAT number format is incorrect'))

            # B2C Double Copy checks
            elif move.tw_invoice_type == 'tw_double':
                # Should not have VAT
                if move.tw_buyer_vat:
                    raise ValidationError(_('Double copy invoice should not have buyer VAT number'))

                # Carrier field checks
                if move.tw_carrier_type != 'none':
                    self._validate_carrier_fields(move)

    def _validate_carrier_fields(self, move):
        """Validate carrier fields"""
        if move.tw_carrier_type == 'mobile_barcode':
            if not move.tw_carrier_num or len(move.tw_carrier_num) != 20:
                raise ValidationError(_('Mobile barcode format error, should be 20 digits'))
            if not move.tw_carrier_num.startswith('/'):
                raise ValidationError(_('Mobile barcode must start with /'))

        elif move.tw_carrier_type == 'citizen_cert':
            if not move.tw_carrier_num or len(move.tw_carrier_num) != 16:
                raise ValidationError(_('Citizen certificate format error, should be 16 characters'))
            if not move.tw_carrier_num[:2].isalpha():
                raise ValidationError(_('Citizen certificate first 2 characters must be letters'))

        elif move.tw_carrier_type == 'donation_code':
            if not move.tw_carrier_num or len(move.tw_carrier_num) != 7:
                raise ValidationError(_('Donation code format error, should be 7 digits'))
            if not move.tw_carrier_num.isdigit():
                raise ValidationError(_('Donation code must be numeric'))

    def _validate_tw_vat(self, vat):
        """Taiwan VAT number validation logic"""
        if not vat or len(vat) != 8:
            return False
        if not vat.isdigit():
            return False
        # Taiwan VAT logic validation (simplified)
        return True

    def action_post(self):
        """Post invoice and record carrier history"""
        result = super().action_post()

        for move in self:
            if move.tw_invoice_type == 'tw_double' and move.tw_carrier_type != 'none':
                self._create_carrier_history(move)

        return result

    def _create_carrier_history(self, move):
        """Create carrier usage history record"""
        self.env['tw.invoice.carrier.history'].create({
            'invoice_id': move.id,
            'partner_id': move.partner_id.id,
            'carrier_type': move.tw_carrier_type,
            'carrier_num': move.tw_carrier_num,
            'invoice_date': move.date,
            'invoice_amount': move.amount_total,
            'donation_unit': move.tw_donation_unit if move.tw_carrier_type == 'donation_code' else False,
        })
