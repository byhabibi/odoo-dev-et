import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.tools import populate
from odoo.exceptions import ValidationError

class MrpProduction(models.Model):
    _inherit = "mrp.production"
    
    is_approved = fields.Boolean('Is Approve', copy=False)
    approval_line_ids = fields.One2many('dsn.mrp.production.approval.line', 'mrp_production_id', string="Approval Line", copy=False)
    approval_mrp_id = fields.Many2one('dsn.approval.mrp', string="Approver Mrp", compute="_compute_approval_mrp_id")
    approval_rule = fields.Selection(related="approval_mrp_id.approval_rule", string="Approval Rule", copy=False)
    approval_type = fields.Selection(related="approval_mrp_id.approval_type", string="Approval Type", copy=False)
    models = fields.Selection(related="approval_mrp_id.models", string="Model")


    @api.depends('name')
    def _compute_approval_mrp_id(self):
        for rec in self:
            rec.approval_mrp_id = self.env['dsn.approval.mrp'].search([('models', '=', 'manufacture_order')], limit=1).id



class DsnMrpProductionApprovalLine(models.Model):
    _name = 'dsn.mrp.production.approval.line'
    _description = "DSN Manufacture Order Approval Line"

    mrp_production_id = fields.Many2one('mrp.production', string="Manufacture Order")
    is_approved = fields.Boolean(string="Is Approved")
    date_approved = fields.Datetime(string="Date Approved")
    user_id = fields.Many2one('res.users', string="User")
    signature = fields.Binary(related='user_id.employee_id.signature', string="Signature")