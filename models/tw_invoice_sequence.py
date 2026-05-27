# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TwInvoiceSequence(models.Model):
    _name = 'tw.invoice.sequence'
    _description = 'Taiwan Invoice Track Management'
    _order = 'period_id desc, start_number'

    name = fields.Char(string='Track Name', required=True, help='e.g., AB Track')
    prefix = fields.Char(
        string='Track Prefix',
        required=True,
        size=2,
        help='2-letter track prefix (e.g., AB)'
    )

    # Period management
    period_id = fields.Many2one(
        'tw.invoice.period',
        string='Invoice Period',
        required=True,
        help='2-month period (e.g., 2024-01, 2024-02)'
    )

    # Number range
    start_number = fields.Integer(string='Start Number', required=True, default=1)
    end_number = fields.Integer(string='End Number', required=True)
    current_number = fields.Integer(string='Current Number', default=1)

    # Journal assignment
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain=[('type', '=', 'sale')],
        help='Sales journal for this track'
    )

    # Status
    active = fields.Boolean(string='Active', default=True)
    is_exhausted = fields.Boolean(
        string='Is Exhausted',
        compute='_compute_is_exhausted',
        store=True
    )

    # Usage statistics
    used_count = fields.Integer(string='Used Count', default=0)

    _prefix_period_unique = models.Constraint(
        'unique(prefix, period_id)',
        'Track prefix must be unique per period',
    )
    _number_range_positive = models.Constraint(
        'CHECK(end_number >= start_number)',
        'End number must be greater than start number',
    )

    @api.depends('current_number', 'end_number')
    def _compute_is_exhausted(self):
        """Check if track is exhausted"""
        for track in self:
            track.is_exhausted = track.current_number > track.end_number

    @api.constrains('prefix')
    def _check_prefix(self):
        """Validate track prefix format"""
        for track in self:
            if track.prefix and not track.prefix.isalpha():
                raise ValidationError(_('Track prefix must be 2 letters'))

    @api.constrains('start_number', 'end_number')
    def _check_number_range(self):
        """Validate number range"""
        for track in self:
            if track.end_number <= track.start_number:
                raise ValidationError(_('End number must be greater than start number'))
            if track.end_number - track.start_number > 99999999:
                raise ValidationError('Number range is too large')

    def get_next_invoice_number(self):
        """Get next invoice number from sequence"""
        self.ensure_one()

        if self.is_exhausted:
            raise ValidationError(_('Track %s is exhausted') % self.name)

        invoice_number = "%s%08d" % (self.prefix, self.current_number)

        # Increment current number
        self.current_number += 1
        self.used_count += 1

        return invoice_number

    def reset_sequence(self, new_start_number=None):
        """Reset sequence to new start number"""
        self.ensure_one()

        if new_start_number:
            self.start_number = new_start_number

        self.current_number = self.start_number
        self.used_count = 0

    @api.model
    def get_active_track(self, journal_id, period_id=None):
        """Get active track for journal and period"""
        domain = [
            ('journal_id', '=', journal_id),
            ('active', '=', True),
        ]

        if period_id:
            domain.append(('period_id', '=', period_id))

        track = self.search(domain, limit=1)

        if not track:
            raise ValidationError(_('No active invoice track found for this journal'))

        return track


class TwInvoicePeriod(models.Model):
    _name = 'tw.invoice.period'
    _description = 'Taiwan Invoice Period Management'
    _order = 'start_date desc'

    name = fields.Char(
        string='Period Name',
        required=True,
        help='e.g., 2024-01, 2024-02'
    )

    # Date range
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    # Period status
    active = fields.Boolean(string='Active', default=True)
    is_closed = fields.Boolean(string='Is Closed', default=False)

    # Statistics
    invoice_count = fields.Integer(string='Invoice Count', default=0)
    total_amount = fields.Float(string='Total Invoice Amount', default=0)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate date range"""
        for period in self:
            if period.end_date < period.start_date:
                raise ValidationError(_('End date must be after start date'))

            # Check if period is exactly 2 months
            from datetime import timedelta
            delta = period.end_date - period.start_date
            expected_days = 60  # Approx 2 months
            if abs(delta.days - expected_days) > 5:  # Allow 5 days variance
                raise ValidationError(_('Period should be approximately 2 months'))

    @api.model
    def get_current_period(self):
        """Get current active period"""
        today = fields.Date.context_today(self)
        period = self.search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
            ('active', '=', True),
        ], limit=1)

        if not period:
            # Create new period if needed
            # Implementation would auto-generate 2-month periods
            pass

        return period

    def close_period(self):
        """Close period and all related tracks"""
        for period in self:
            period.is_closed = True
            period.active = False

            # Close all tracks in this period
            tracks = self.env['tw.invoice.sequence'].search([
                ('period_id', '=', period.id)
            ])
            tracks.write({'active': False})
