from datetime import date

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        refund = self.env['account.invoice.refund'].create({
            'filter_refund': 'refund',
            'description': 'Return product',
            'date_invoice': date.today(),
        })

        context = dict(self._context or {})
        order = self.env['stock.picking'].browse(context.get('active_ids')).sale_id
        action = super(StockReturnPicking, self).create_returns()
        invoice = self.env['account.invoice'].search([('original_invoice', '=', True), (
            'order_id', '=', order.id)])
        refund.with_context({'active_ids': [invoice.id]}).compute_refund(mode='refund')
        credit_note = self.env['account.invoice'].search([('refund_invoice_id', '=', invoice.id)])
        for e in credit_note:
            if e.state != 'paid':
                e.action_invoice_open()
                if order.payment_method == 'cod':
                    journal_id = self.env['account.journal'].search([('code', '=', 'CSH1')]).id
                elif order.payment_method == 'online_payment':
                    journal_id = self.env['account.journal'].search([('code', '=', 'BNK1')]).id
                payment = self.env['account.payment'].create({
                    'invoice_ids': [(4, e.id, None)],
                    'amount': e.amount_total,
                    'payment_date': date.today(),
                    'communication': e.number,
                    'payment_type': 'outbound',
                    'journal_id': journal_id,
                    'partner_type': 'customer',
                    'payment_method_id': 1,
                    'partner_id': e.partner_id.id
                })
                payment.action_validate_invoice_payment()
        return action
