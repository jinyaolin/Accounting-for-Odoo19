# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TwDonationUnit(models.Model):
    _name = 'tw.donation.unit'
    _description = 'Taiwan Donation Code Units'
    _order = 'code'

    code = fields.Char(string='Unit Code', size=7, required=True)
    name = fields.Char(string='Unit Name', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Statistics
    donation_count = fields.Integer(string='Donation Count', compute='_compute_donation_count')
    total_amount = fields.Float(string='Total Donation Amount', compute='_compute_donation_amount')

    @api.depends('code')
    def _compute_donation_count(self):
        """Calculate donation count"""
        for unit in self:
            unit.donation_count = self.env['tw.invoice.carrier.history'].search_count([
                ('donation_unit', '=', unit.code)
            ])

    @api.depends('code')
    def _compute_donation_amount(self):
        """Calculate total donation amount"""
        for unit in self:
            histories = self.env['tw.invoice.carrier.history'].search([
                ('donation_unit', '=', unit.code)
            ])
            unit.total_amount = sum(histories.mapped('invoice_amount'))

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Donation unit code must be unique'),
    ]
