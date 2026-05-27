# -*- coding: utf-8 -*-
{
    'name': 'Taiwan Accounting Localization',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Taiwan accounting localization and tax compliance for Odoo 19',
    'description': """
Taiwan Accounting Localization for Odoo 19
==========================================

Complete accounting localization for Taiwan trade companies:

Core Features:
    * Taiwan Chart of Accounts
    * Uniform Invoice System (E-invoice)
    * B2B/B2C Auto Detection
    * Carrier Management (Mobile Barcode, Citizen Certificate, Donation Code)
    * VAT Tax Calculation and Reporting
    * Financial Statements (Taiwan Format)
    * Trade Accounting (Import/Export)
    * Electronic Invoice Integration

This module ensures full compliance with Taiwan's business accounting law
and tax regulations, specifically designed for trading companies.

Phase 1 (Week 1-4): Core Compliance & Invoice Issuance
Phase 2 (Week 5-8): Tax Reporting & Trade Features
Phase 3 (Week 9-12): Advanced Features & Optimization
    """,
    'author': 'jinyaolin',
    'website': 'https://github.com/jinyaolin',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',           # Core accounting module
        'base_vat',         # VAT handling
        'stock',            # Inventory (for trade features)
        'purchase',         # Suppliers
        'sale',             # Customers
    ],
    'data': [
        # Security
        # 'security/tw_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/tw_chart_of_accounts_data.xml',
        'data/tw_cash_management_data.xml',
        'data/tw_tax_rates_data.xml',

        # Views (order matters: actions before menus that reference them)
        'views/tw_account_views.xml',
        'views/tw_account_management_views.xml',
        'views/tw_invoice_views.xml',
        'views/tw_partner_views.xml',
        # 'views/tw_donation_unit_views.xml',  # Temporarily disabled
        'views/tw_wizards_views.xml',
        'views/tw_cash_management_views.xml',
        'views/tw_exchange_rate_views.xml',
        'views/tw_menu.xml',  # Must be last - references actions from above
    ],
    'assets': {
        'web.assets_backend': [
            # 'tw_accounting/static/src/css/tw_accounting.css',
            # 'tw_accounting/static/src/js/tw_invoice_widgets.js',
        ],
    },
    # 'images': [
    #     'static/description/icon.png',
    #     'static/description/banner.png',
    # ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
