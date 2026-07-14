import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

#  ================================\approval\========================================>
class DsnApprovaSale(models.Model):
    _name = "dsn.approval.sale"
    _description = "DSN Approval Sale"
    _rec_name = 'reference'

    reference = fields.Char("Reference")
    models = fields.Selection(
        [('quotation', 'Quotation'), 
        ('loi', 'LOI'),
        ], string="Model", default="quotation")
    approval_type = fields.Selection([('position-base-approval', 'Position Base Approval'), ('individual-base-approval', 'Individual Base Approval')], default="position-base-approval")
    approval_rule = fields.Selection([('only-one-approved', 'Only One Approved'), ('all-approved', 'All Approved')], default="only-one-approved")

    user_ids = fields.One2many('dsn.sale.approval.user.line', 'approval_sale_id', string='Approver')
    job_ids = fields.One2many('dsn.sale.approval.job.line', 'approval_sale_id', string='Job Position')

    @api.constrains('user_ids')
    def _constrains_user_ids(self):
        for this in self:
            if this.approval_type == 'individual-base-approval' and len(this.user_ids) == 0:
                raise ValidationError(_("Don't leave the user ids line blank if you set individual base approval!"))
    
    @api.constrains('job_ids')
    def _constrains_job_ids(self):
        for this in self:
            if this.approval_type == 'position-base-approval' and len(this.job_ids) == 0:
                raise ValidationError(_("Don't leave the job ids line blank if you set position base approval!"))

    @api.constrains('models')
    def _constrains_double_data(self):
        for this in self:
            datas = self.search([('models', '=', this.models)])
            if len(datas) > 1:
                raise ValidationError(_('Approval for %s document already exist!', this.models))
            
    @api.constrains('reference')
    def _constrains_double_data(self):
        for this in self:
            datas = self.search([('reference', '=', this.reference)])
            if len(datas) > 1:
                raise ValidationError(_('Approval for reference %s already exist!', this.reference))
        
#  ================================\user ids\========================================>
class DsnSaleApprovalUserLine(models.Model):
    _name = "dsn.sale.approval.user.line"
    _description = "DSN Sale Approval User Line"

    sequence = fields.Integer(string='Sequence')
    user_id = fields.Many2one('res.users', string="User")
    approval_sale_id = fields.Many2one('dsn.approval.sale', string="Approver Sale")
    
#  ================================\job ids\========================================>
class DsnSaleApprovalJobLine(models.Model):
    _name = "dsn.sale.approval.job.line"
    _description = "DSN Sale Approval Job Line"

    sequence = fields.Integer(string='Sequence')
    job_id = fields.Many2one('hr.job', string="Job Position")
    approval_sale_id = fields.Many2one('dsn.approval.sale', string="Approver Sale")