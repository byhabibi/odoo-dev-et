from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

class SettingInventorySequence(models.Model):
    _name = 'dsn.inventory.sequence.setting'
    _inherit = ['mail.thread']
    _rec_name = 'type'
    _description = 'Inventory Setting Sequence'

    type = fields.Selection([
        ('landed_cost', 'Landed Cost'),
        ('transfer', 'Transfer'),
        ('scrap', 'Scrap')
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