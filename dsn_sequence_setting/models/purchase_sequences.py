from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

class SettingPurchaseSequence(models.Model):
    _name = 'dsn.purchase.sequence.setting'
    _inherit = ['mail.thread']
    _rec_name = 'type'
    _description = 'Purchase Setting Sequence'

    type = fields.Selection([
        ('purchase_request', 'Purchase Request'),
        ('purchase_order', 'Purchase Order')
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
        
    def update_sequence_code(self):
        if self.sequence_id:
            suffix = '/' + str(self.code) + '/' + '%(month)s' + '/' + '%(y)s'
            val = {
                'code' : str(self.type) + ' - ' + self.code,
                'suffix' : suffix
                }
            
            self.sequence_id.update(val)

    @api.constrains('type','company_id')
    def _constrains_double_data(self):
        datas = self.search([('type', '=', self.type),('company_id', '=', self.company_id.id)])
        if len(datas) > 1:
            raise UserError(_('Data %s with %s Already Exist!', self.type, self.company_id.display_name))
        
    def unlink(self):
        if self.sequence_id:
            raise UserError(_('You Must delete this sequence in master sequence!'))
        return super().unlink()
    

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    @api.model
    def create(self,values):
        sequences_setting = self.env['dsn.purchase.sequence.setting'].search([
            ('type', '=', 'purchase_order'), ('company_id', '=', self.env.company.id)], limit=1)
        
        if not sequences_setting or not sequences_setting.sequence_id:
            raise UserError("You must set sequence Purchase Order in Purchase Sequences Settings")
        
        new_name = sequences_setting.sequence_id.next_by_id(sequence_date=fields.date.today())

        if 'name' in values:
            if values['name'] == 'New':
                values['sequence_number'] = 0
                values['parent_revision_name'] = new_name
                values['name'] = new_name
        else:
            values['sequence_number'] = 0
            values['parent_revision_name'] = new_name
            values['name'] = new_name
        
        res = super(PurchaseOrder, self).create(values)
        return res
    
    sequence_number = fields.Integer(string='Sequence Number')
    parent_revision_name = fields.Char('Parent Revision Name')
    
class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
    
    @api.model
    def create(self,values):
        sequences_setting = self.env['dsn.purchase.sequence.setting'].search([
            ('type', '=', 'purchase_request'), ('company_id', '=', self.env.company.id)], limit=1)
        
        if not sequences_setting or not sequences_setting.sequence_id:
            raise UserError("You must set sequence Purchase Request in Purchase Sequences Settings")
        
        new_name = sequences_setting.sequence_id.next_by_id(sequence_date=fields.date.today())

        if 'name' in values:
            if values['name'] == 'New':
                values['sequence_number'] = 0
                values['parent_revision_name'] = new_name
                values['name'] = new_name
        else:
            values['sequence_number'] = 0
            values['parent_revision_name'] = new_name
            values['name'] = new_name
        
        res = super(PurchaseRequest, self).create(values)
        return res
    
    sequence_number = fields.Integer(string='Sequence Number')
    parent_revision_name = fields.Char('Parent Revision Name')

