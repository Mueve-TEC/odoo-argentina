from odoo import fields, models, _, api
from odoo.exceptions import UserError
from functools import partial

import json
import base64
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
            'to_invoice': ui_order['to_invoice'] if "to_invoice" in ui_order else False,
            'to_ship': ui_order['to_ship'] if "to_ship" in ui_order else False,
            'is_tipped': ui_order.get('is_tipped', False),
            'tip_amount': ui_order.get('tip_amount', 0),
        }



    @api.model
    def create(self, values):
        values['to_invoice'] = True
        return super(PosOrder, self).create(values)


    def _is_electronic_invoice_journal(self, journal):
        """Check if a journal is configured for AFIP electronic invoicing"""
        return (
            journal.l10n_ar_afip_pos_system in ['RLI_RLM', 'FEERCEL'] and
            hasattr(journal, 'afip_ws') and
            journal.afip_ws
        )


    def _generate_pos_order_invoice(self):
        """Override to integrate AFIP validation for electronic invoices"""
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

            order.write({'account_move': new_move.id, 'state': 'invoiced'})

            # Check if journal is configured for AFIP electronic invoicing
            is_electronic_journal = order._is_electronic_invoice_journal(new_move.journal_id)

            if is_electronic_journal:
                logger.info('Processing electronic invoice %s for POS order %s', new_move.name, order.name)
                
                try:
                    # Post the invoice to trigger AFIP validation
                    new_move.sudo().with_company(order.company_id).action_post()
                    logger.info('Electronic invoice %s processed successfully', new_move.name)
                    logger.info('AFIP CAE for invoice %s: %s', new_move.name, new_move.afip_auth_code)    

                except Exception as e:
                    logger.error('Error processing electronic invoice %s: %s', new_move.name, str(e))
                    # Keep invoice in draft state and show error message
                    new_move.message_post(body=_('Error processing electronic invoice: %s') % str(e))
                    
                    raise UserError(_('Error processing AFIP electronic invoice: %s') % str(e))
                    
            else:
                # For non-electronic invoices, we use the standard post method
                new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True)._post()

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
            'res_id': moves and moves.ids[0] or False,
        }

