import logging
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.tools import populate
from odoo.exceptions import ValidationError

class DsnApprovalMrp(models.Model):
    _name = "dsn.approval.mrp"
    _description = "DSN Approval Mrp"
    _rec_name = 'reference'


    reference = fields.Char("Reference")
    models = fields.Selection(
        [('mrp_production', 'Manufacture Order')
        ], string="Model", default="mrp_production")
    approval_type = fields.Selection([('position-base-approval', 'Position Base Approval'), ('individual-base-approval', 'Individual Base Approval')], default="position-base-approval")
    approval_rule = fields.Selection([('only-one-approved', 'Only One Approved'), ('all-approved', 'All Approved')], default="only-one-approved")

    user_ids = fields.One2many('dsn.mrp.approval.user.line', 'approval_mrp_id', string='Approver')
    job_ids = fields.One2many('dsn.mrp.approval.job.line', 'approval_mrp_id', string="Job Position")



class DsnMrpApprovalUserLine(models.Model):
    _name = "dsn.mrp.approval.user.line"
    _description = "DSN Mrp Approval User Line"

    sequence = fields.Integer(string='Sequence')
    user_id = fields.Many2one('res.users', string="User")
    approval_mrp_id = fields.Many2one('dsn.approval.mrp', string="Approver Manufacture Order")


class DsnMrpApprovalJobLine(models.Model):
    _name = "dsn.mrp.approval.job.line"
    _description = "DSN Mrp Approval Job Line"

    sequence = fields.Integer(string='Sequence')
    job_id = fields.Many2one('hr.job', string="Job Position")
    approval_mrp_id = fields.Many2one('dsn.approval.mrp', string="Approver Manufacture Order")
