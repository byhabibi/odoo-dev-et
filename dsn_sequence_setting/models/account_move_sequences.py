from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class SettingAccountSequence(models.Model):
    _name = 'dsn.account.move.sequence.setting'
    _inherit = ['mail.thread']
    _rec_name = 'type'
    _description = 'Account Setting Sequence'

    type = fields.Selection([
        ('invoice', 'Invoice'),
        ('bill', 'Bill'),
        ('credit_note', 'Credit Note'),
        ('refund', 'Refund')
    ], tracking=True)
    code = fields.Char(string='Code', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', tracking=True)
    sequence_id = fields.Many2one('ir.sequence', string='Sequence', trakcing=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], string='State', default='draft')

    def create_sequence(self):
        suffix = '/' + str(self.code) + '/' + '%(month)s' + '/' + '%(y)s'
        values = {
            'name' : str(self.type),
            'code' : str(self.type) + ' - ' + self.code,
            'suffix' : suffix,
            'number_next' : 1,
            'number_increment' : 1,
            'use_date_range' : True,
            'padding' : 5,
            'company_id' : self.company_id.id
        }
        sequence = self.env['ir.sequence'].create(values)
        self.write({'sequence_id': sequence.id, 'state': 'confirm'})
        
        # if self.type in ['invoice', 'credit_note']:
        #     journal = self.env['account.journal'].sudo().search([('type', '=', 'sale')])
        #     for rec in journal:
        #         if 'invoice' in rec.name.lower():
        #             if self.type == 'invoice':
        #                 rec.write({'code': self.code, 'sequence_id': sequence.id})
                        
        #             if self.type == 'credit_note':
        #                 rec.write({'refund_sequence_id': sequence.id})
                        
        # else:
        #     journal = self.env['account.journal'].sudo().search([('type', '=', 'purchase')])
        #     for rec in journal:
        #         if 'bill' in rec.name.lower():
        #             if self.type == 'bill':
        #                 rec.write({'code': self.code, 'sequence_id': sequence.id})
                        
        #             if self.type == 'refund':
        #                 rec.write({'refund_sequence_id': sequence.id})
                        
        
    def update_sequence_code(self):
        suffix = '/' + str(self.code) + '/' + '%(month)s' + '/' + '%(y)s'
        self.sequence_id.update({'suffix': suffix})
        journal = self.env['account.journal'].sudo().search([('sequence_id', '=', self.sequence_id.id)], limit=1)
        if journal and self.type in ['invoice', 'bill']:
            for rec in journal:
                rec.update({'code': self.code})
        

    @api.constrains('type','company_id')
    def _constrains_double_data(self):
        datas = self.search([('type', '=', self.type),('company_id', '=', self.company_id.id)])
        if len(datas) > 1:
            raise UserError(_('Data %s with %s Already Exist!', self.type, self.company_id.display_name))
        
    def unlink(self):
        if self.sequence_id:
            raise UserError(_('You Must delete this sequence in master sequence!'))
        return super().unlink()
    
# class AccountMove(models.Model):
#     _inherit = 'account.move'
    
#     name = fields.Char(string='Number', compute=False, required=True, readonly=False, copy=False, default='/')
    
#     def _get_sequence(self):
#         self.ensure_one()
#         journal = self.journal_id
#         if self.move_type in ('out_invoice', 'in_invoice') or not journal.refund_sequence:
#             return journal.sequence_id
#         if not journal.refund_sequence_id:
#             return
#         return journal.refund_sequence_id

#     def _post(self, soft=True):
#         for move in self:
#             if move.move_type == 'out_invoice':
#                 sequences_setting = self.env['dsn.account.move.sequence.setting'].search([
#                 ('type', '=', 'invoice'), ('company_id', '=', self.env.company.id)], limit=1)
            
#                 if not sequences_setting or not sequences_setting.sequence_id:
#                         raise UserError("You must set sequence Invoice in Accounting Sequences Settings")
                
#             if move.move_type == 'out_refund':
#                 sequences_setting = self.env['dsn.account.move.sequence.setting'].search([
#                 ('type', '=', 'credit_note'), ('company_id', '=', self.env.company.id)], limit=1)
            
#                 if not sequences_setting or not sequences_setting.sequence_id:
#                         raise UserError("You must set sequence Credit Note in Accounting Sequences Settings")
                    
#             if move.move_type == 'in_invoice':
#                 sequences_setting = self.env['dsn.account.move.sequence.setting'].search([
#                 ('type', '=', 'bill'), ('company_id', '=', self.env.company.id)], limit=1)
            
#                 if not sequences_setting or not sequences_setting.sequence_id:
#                         raise UserError("You must set sequence Bill in Accounting Sequences Settings")
            
#             if move.move_type == 'in_refund':
#                 sequences_setting = self.env['dsn.account.move.sequence.setting'].search([
#                 ('type', '=', 'refund'), ('company_id', '=', self.env.company.id)], limit=1)
            
#                 if not sequences_setting or not sequences_setting.sequence_id:
#                         raise UserError("You must set sequence Refund in Accounting Sequences Settings")
                
#             if move.name == '/' and move.move_type in ['out_invoice', 'in_invoice', 'in_refund', 'out_refund']:
#                 sequence = move._get_sequence()
#                 if not sequence:
#                     raise UserError(_('Please define a sequence on your journal from Accounting Sequence Setting.'))
#                 move.name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
#         res = super(AccountMove, self)._post(soft=True)
#         return res
    
    
#     @api.onchange('journal_id')
#     def onchange_journal_id(self):
#         self.name = '/'