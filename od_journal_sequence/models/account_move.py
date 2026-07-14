# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    name = fields.Char(string='Number', required=True, readonly=False, copy=False, default='/')

    def _get_sequence(self):
        self.ensure_one()
        journal = self.journal_id
        if self.move_type in ('entry', 'out_invoice', 'in_invoice', 'out_receipt', 'in_receipt') or not journal.refund_sequence:
            return journal.sequence_id
        if not journal.refund_sequence_id:
            return
        return journal.refund_sequence_id

    def _post(self, soft=True):
        for move in self:
            if move.name == '/':
                sequence = move._get_sequence()
                if not sequence:
                    raise UserError(_('Please define a sequence on journal {}.'.format(move.journal_id)))
                move.name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
        res = super(AccountMove, self)._post(soft=True)
        return res

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self.name = '/'

    @api.onchange('invoice_date')
    def _onchange_invoice_date(self):
        if self.invoice_date:
            if not self.invoice_payment_term_id and (not self.invoice_date_due or self.invoice_date_due < self.invoice_date):
                self.invoice_date_due = self.invoice_date
            if self.date != self.invoice_date:  # Don't flag date as dirty if not needed
                self.date = self.invoice_date
            # self._onchange_currency()
            if self.name == '/':
                self.name = '/'
                _logger.info('----------------------*invoice date new*----------------------')
            if self.invoice_date.year > datetime.today().year :
                self.name = '/'
            elif self.invoice_date.year == datetime.today().year :
                if self.invoice_date.month > datetime.today().month :
                    self.name = '/'
                elif self.invoice_date.month == datetime.today().month :
                    if self.invoice_date.day > datetime.today().day :
                        self.name = '/'

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        _logger.info('----------------------*Account Move*----------------------')
        _logger.info(vals.get('invoice_date'))
        if vals.get('invoice_date') :
            try :
                dt_obj = datetime.strptime(vals.get('invoice_date'), '%Y-%m-%d')
            except :
                date_time = vals.get('invoice_date').strftime('%Y-%m-%d')
                dt_obj = datetime.strptime(date_time, '%Y-%m-%d')
            
            _logger.info(dt_obj.year)
            if dt_obj.year > datetime.today().year :
                self.name = '/'
            elif dt_obj.year == datetime.today().year :
                if dt_obj.month > datetime.today().month :
                    self.name = '/'
        return res