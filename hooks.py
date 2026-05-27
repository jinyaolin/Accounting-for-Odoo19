# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)


def _post_init_hook(env):
    """Auto-configure all settings needed for Taiwan accounting on fresh install"""
    # 0. Prevent generic_coa chart template from loading and wiping our data.
    #    When the 'account' module is installed, it defers loading of generic_coa
    #    into registry._auto_install_template (see account/models/ir_module.py).
    #    That runs in _register_hook() AFTER all modules load, deleting all
    #    existing account.account / account.tax / account.journal records.
    #    Since tw_accounting provides its own Taiwan chart, we cancel it.
    if hasattr(env.registry, '_auto_install_template'):
        logger.info('Canceling deferred generic_coa auto-install to preserve Taiwan chart of accounts')
        del env.registry._auto_install_template

    # 1. Ensure essential journals exist (before configuring payment accounts)
    _ensure_journals(env)

    # 2. Set default receivable/payable accounts for new partners
    _set_default_partner_accounts(env)

    # 3. Configure payment method lines on bank/cash journals
    _configure_journal_payment_accounts(env)

    # 4. Set product category default income/expense accounts
    _set_product_category_accounts(env)


def _set_default_partner_accounts(env):
    """Set default receivable/payable accounts via ir.default"""
    receivable = env['account.account'].search([
        ('account_type', '=', 'asset_receivable'),
    ], limit=1)
    payable = env['account.account'].search([
        ('account_type', '=', 'liability_payable'),
    ], limit=1)

    if receivable:
        env['ir.default'].set(
            'res.partner', 'property_account_receivable_id',
            receivable.id, company_id=env.company.id,
        )
        logger.info('Set default receivable account: %s (%s)', receivable.name, receivable.code)

    if payable:
        env['ir.default'].set(
            'res.partner', 'property_account_payable_id',
            payable.id, company_id=env.company.id,
        )
        logger.info('Set default payable account: %s (%s)', payable.name, payable.code)


def _configure_journal_payment_accounts(env):
    """Set payment_account_id on bank/cash journal payment method lines"""
    Account = env['account.account']

    bank_account = Account.search([('code', '=', '1110002')], limit=1)
    cash_account = Account.search([('code', '=', '1110001')], limit=1)

    for journal in env['account.journal'].search([('type', 'in', ['bank', 'cash'])]):
        if journal.type == 'bank' and bank_account:
            payment_account = bank_account
        elif journal.type == 'cash' and cash_account:
            payment_account = cash_account
        else:
            continue

        for line in journal.inbound_payment_method_line_ids:
            if not line.payment_account_id:
                line.payment_account_id = payment_account.id
                logger.info(
                    'Set inbound payment account on %s: %s (%s)',
                    journal.name, payment_account.name, payment_account.code,
                )

        for line in journal.outbound_payment_method_line_ids:
            if not line.payment_account_id:
                line.payment_account_id = payment_account.id
                logger.info(
                    'Set outbound payment account on %s: %s (%s)',
                    journal.name, payment_account.name, payment_account.code,
                )


def _set_product_category_accounts(env):
    """Set income/expense accounts on all product categories"""
    Account = env['account.account']

    income_account = Account.search([
        ('code', '=', '4100000'),
    ], limit=1)  # 銷貨收入
    expense_account = Account.search([
        ('code', '=', '5100000'),
    ], limit=1)  # 銷貨成本

    if not income_account or not expense_account:
        logger.warning('TW income/expense accounts not found, skipping product category setup')
        return

    for cat in env['product.category'].search([]):
        if not cat.property_account_income_categ_id:
            cat.property_account_income_categ_id = income_account.id
            logger.info('Set income account on category %s: %s', cat.name, income_account.code)
        if not cat.property_account_expense_categ_id:
            cat.property_account_expense_categ_id = expense_account.id
            logger.info('Set expense account on category %s: %s', cat.name, expense_account.code)

    # Also set as ir.default for new categories
    env['ir.default'].set(
        'product.category', 'property_account_income_categ_id',
        income_account.id, company_id=env.company.id,
    )
    env['ir.default'].set(
        'product.category', 'property_account_expense_categ_id',
        expense_account.id, company_id=env.company.id,
    )
    logger.info('Set default product category accounts: income=%s, expense=%s',
                income_account.code, expense_account.code)


def _ensure_journals(env):
    """Ensure essential journals exist (bank, sales, purchase)"""
    Journal = env['account.journal']

    # Bank journal
    if not Journal.search([('type', '=', 'bank')], limit=1):
        Journal.create({
            'name': '銀行存款',
            'code': 'BANK',
            'type': 'bank',
        })
        logger.info('Created bank journal: 銀行存款')

    # Sales journal (needed for invoices)
    if not Journal.search([('type', '=', 'sale')], limit=1):
        Journal.create({
            'name': '銷貨',
            'code': 'SALE',
            'type': 'sale',
        })
        logger.info('Created sales journal: 銷貨')

    # Purchase journal (needed for vendor bills)
    if not Journal.search([('type', '=', 'purchase')], limit=1):
        Journal.create({
            'name': '進貨',
            'code': 'PURC',
            'type': 'purchase',
        })
        logger.info('Created purchase journal: 進貨')
