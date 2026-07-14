from odoo import api, fields, models, _
from odoo.tools import populate
import logging
_logger = logging.getLogger(__name__)

class DsnHrEmployeeApprover(models.Model):
    _name = "dsn.hr.employee.approver"
    _description = "DSN Employee Approver"

    job_id = fields.Many2one('hr.job', string="Job Position")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee")
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
    user_id = fields.Many2one('res.users', string="Approver", required=True, help="Approver",)
    user_ids = fields.Many2many('res.users', string="Filtered Approver", compute="_compute_user_ids")

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for rec in self:
            rec.user_id = False

    @api.depends('job_id')
    def _compute_user_ids(self):
        user_ids = self.env['res.users'].search([('company_id', '=', self.company_id.id)])
        filtered_user = []
        for user in user_ids:
            if user.employee_id.job_id == self.job_id:
                filtered_user.append(user.id)
        self.user_ids = filtered_user

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    approver_ids = fields.One2many("dsn.hr.employee.approver", 'employee_id', string="Approver")
    signature = fields.Binary(string='Signature')