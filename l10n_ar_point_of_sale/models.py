from odoo import fields, models, _, api
from odoo.exceptions import UserError
from functools import partial

import logging

logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    to_invoice = fields.Boolean('To invoice', default=True)

    @api.model
    def _order_fields(self, ui_order):
        process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
        if not ui_order.get('partner_id'):
            ui_order['partner_id'] = self.env.ref('l10n_ar.par_cfa') and self.env.ref('l10n_ar.par_cfa').id or False
        # Refunds must always be invoiced because they need the related credit
        # note, no matter what the frontend sends.
        to_invoice = ui_order.get('to_invoice', True)
        if ui_order.get('amount_total', 0) < 0:
            to_invoice = True
        return {
            'user_id':      ui_order['user_id'] or False,
            'session_id':   ui_order['pos_session_id'],
            'lines':        [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'pos_reference': ui_order['name'],
            'sequence_number': ui_order['sequence_number'],
            'partner_id':   ui_order['partner_id'] or False,
            'date_order':   ui_order['creation_date'].replace('T', ' ')[:19],
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'pricelist_id': ui_order['pricelist_id'],
            'amount_paid':  ui_order['amount_paid'],
            'amount_total':  ui_order['amount_total'],
            'amount_tax':  ui_order['amount_tax'],
            'amount_return':  ui_order['amount_return'],
            'company_id': self.env['pos.session'].browse(ui_order['pos_session_id']).company_id.id,
            'to_invoice': to_invoice,
            'to_ship': ui_order['to_ship'] if "to_ship" in ui_order else False,
            'is_tipped': ui_order.get('is_tipped', False),
            'tip_amount': ui_order.get('tip_amount', 0),
        }

    @api.model_create_multi
    def create(self, vals_list):
        # Refunds (negative orders) must always generate their credit note.
        for values in vals_list:
            if values.get('amount_total', 0) < 0:
                values['to_invoice'] = True
        return super(PosOrder, self).create(vals_list)

    def _prepare_invoice_vals(self):
        """Make POS refunds reference the original ARCA electronic invoice.

        The credit note must inform the associated voucher (CbteAsoc) using the
        point of sale and number of the original invoice, so we keep
        `reversed_entry_id` pointing to it (``get_related_invoices_data`` reads
        that field). Without it, a POS refund cannot be authorized by ARCA.
        """
        origin_orders = self.refunded_order_ids
        # Core would crash with "Expected singleton" when a single refund
        # references several invoiced orders; raise something readable instead.
        if len(origin_orders.mapped('account_move')) > 1:
            raise UserError(_(
                'Solo se puede devolver una factura electrónica a la vez.'))
        vals = super()._prepare_invoice_vals()
        if self.amount_total >= 0:
            return vals
        origin_invoices = origin_orders.mapped('account_move').filtered(
            lambda move: move.journal_id.l10n_ar_afip_pos_system in
            ['RLI_RLM', 'FEERCEL'])
        electronic = origin_invoices.filtered(lambda move: move.afip_auth_code)
        if len(electronic) > 1:
            raise UserError(_(
                'Solo se puede devolver una factura electrónica a la vez.'))
        if electronic:
            vals['reversed_entry_id'] = electronic.id
        elif origin_invoices:
            raise UserError(_(
                'No se encontró la factura electrónica original con CAE para '
                'la devolución. La nota de crédito debe informar el punto de '
                'venta y número de la factura original (CbteAsoc). Verifique '
                'que la factura original esté autorizada por AFIP.'))
        return vals

    def _generate_pos_order_invoice(self):
        """Generate the invoice for the validated POS orders.

        The invoice is posted *before* the order is linked/marked as invoiced.
        For electronic journals the CAE is requested before the move is posted
        (see ``l10n_ar_afipws_fe.action_post``), so a rejected invoice stays in
        draft and never shows up confirmed in the journal.
        """
        moves = self.env['account.move']
        logger.info('Generating invoices for POS orders during validation: %s', self.mapped('name'))

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                logger.info('No partner for order %s, skipping invoice creation', order.name)
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)

            new_move.sudo().with_company(order.company_id).with_context(
                skip_invoice_sync=True).action_post()

            # Link the order only once the invoice was actually posted.
            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            moves += new_move

            payment_moves = order._apply_invoice_payments(order.session_id.state == 'closed')
            if order.session_id.state == 'closed':  # If the session isn't closed this isn't needed.
                # If a client requires the invoice later, we need to revers the amount from the closing entry, by making a new entry for that.
                order._create_misc_reversal_move(payment_moves)

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves.ids[0] if moves else False,
        }
