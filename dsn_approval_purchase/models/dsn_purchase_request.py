import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.tools import populate
from odoo.exceptions import ValidationError

class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    approval_line_ids = fields.One2many('dsn.purchase.request.approval.line', 'purchase_request_id', string="Approval Line", )
    approval_purchase_id = fields.Many2one('dsn.approval.purchase', string="Approver Purchase", compute="_compute_approval_purchase_id")
    approval_rule = fields.Selection(related="approval_purchase_id.approval_rule", string="Approval Rule")
    approval_type = fields.Selection(related="approval_purchase_id.approval_type", string="Approval Type")
    assigned_to_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approver",
    )
    models = fields.Selection(related="approval_purchase_id.models", string="Model")
    user_in_assigned_to = fields.Boolean(string="User Is Assigned", compute="_computed_user_in_assigned_to")

    def _computed_user_in_assigned_to(self):
        if self.assigned_to_ids and self.state == 'to_approve':
            if self.approval_rule == 'only-one-approved':
                self.user_in_assigned_to = True if self.env.user.id in self.assigned_to_ids.ids else False
            else:
                for appr in self.approval_line_ids:
                    if appr.is_approved:
                        continue
                    else:
                        self.user_in_assigned_to = True if self.env.user.id == appr.user_id.id else False
                        break
        else:
            self.user_in_assigned_to = False

    def button_rejected(self):
        res = super(PurchaseRequest, self).button_rejected()
        # unlink mail activity
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.request')], limit=1).id
        self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).unlink()
        return res
    
    def button_approved(self):
        # set is approved
        approval_purchase_request = self.env['dsn.purchase.request.approval.line']
        record = self.env['dsn.purchase.request.approval.line'].search([('purchase_request_id', '=', self.id), ('user_id', '=', self.env.user.id), ('is_approved', '=', False)], limit=1)
        record.write({'is_approved': True, 'date_approved': datetime.now()})

        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.request')], limit=1).id

        # set state
        if self.approval_rule == 'only-one-approved':
            # self.active_approver = self.assigned_to_ids
            if any(self.approval_line_ids.mapped('is_approved')):
                self.write({"state": "approved"}) 
                # set all mail activity to be done
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).action_done()
                

        # set state
        else:
            is_approved_counted = len(approval_purchase_request.search([('is_approved', '=', True), ('purchase_request_id.models', '=', 'purchase_request'), ('purchase_request_id', '=', self.id)]).ids)
            approval_purchase_request_user = [rec.user_id for rec in approval_purchase_request.search([], order='id asc')]
            # current_user_id = approval_purchase_request_user[is_approved_counted - 1] if is_approved_counted else approval_purchase_request_user[0]

            current_user_id = self.env.user
            index_current_user = approval_purchase_request_user.index(current_user_id)          

            # assign to the next approver
            if all(self.approval_line_ids.mapped('is_approved')):
                self.write({"state": "approved"}) 
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', self.env.user.id)]).action_done()
            else:

                user_id = approval_purchase_request_user[index_current_user+1]
                # _logger.info(user_id)

                # set mail activity to be done one by one
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', self.env.user.id)]).action_done()
                activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
                

                # send notification to the next approver
                self.send_mail_activity(activity_type_id, user_id.id, self.id, res_model_id)

    def send_mail_activity(self, activity_type_id, user_id, res_id, res_model_id):
        self.env["mail.activity"].sudo().create(
            {
                "activity_type_id": activity_type_id,
                "note": _(
                    "You have items in the Purchase Order document that you need to approve "
                    "Check if an action is needed."
                ),
                "user_id": (
                    user_id
                ),
                "res_id": res_id,
                "res_model_id": res_model_id,
                'summary': 'Reminder Purchase Order Approval',
            }
        )

    def button_to_approve(self):
        res = super(PurchaseRequest, self).button_to_approve()
        records = []
        if self.requested_by.sudo().employee_id.approver_ids:
            for appr_line in self.approval_purchase_id:
                if appr_line.approval_type == 'position-base-approval':
                    for job in appr_line.job_ids:
                        if not self.requested_by.sudo().employee_id.approver_ids:
                            raise ValidationError(_("Can't find approver for current user!"))
                                
                        for approver in self.requested_by.sudo().employee_id.approver_ids:
                            if job.job_id.id == approver.job_id.id:
                                records.append(approver.user_id.id)
                                
                                self.env['dsn.purchase.request.approval.line'].create({
                                    'purchase_request_id': self.id,
                                    'user_id': approver.user_id.id,
                                })
                else:
                    for user in appr_line.user_ids:
                        records.append(user.user_id.id)
                        if len(records) == 0:
                            raise ValidationError(_("Can't find approver for current user!"))
                        self.env['dsn.purchase.request.approval.line'].create({
                                'purchase_request_id': self.id,
                                'user_id': user.user_id.id,
                            })
        if len(records) == 0:
            raise ValidationError(_("Can't find approver for current user!"))
        
        self.assigned_to_ids = [(6, 0, records)]

        # send notification 
        activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.request')], limit=1).id

        if self.approval_rule == 'only-one-approved':
            # send notification to the first approver
            for rec in records:
                self.send_mail_activity(activity_type_id, rec, self.id, res_model_id)
        else:
            # send notification to all approver
            self.send_mail_activity(activity_type_id, records[0], self.id, res_model_id)

        return res
    
    def button_draft(self):
        res = super(PurchaseRequest, self).button_draft()
        self.assigned_to_ids = [(6, 0, [])]
        self.env['dsn.purchase.request.approval.line'].search([('purchase_request_id', '=', self.id)]).unlink()
        # unlink mail activity
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.request')], limit=1).id
        self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).unlink()
        return res

    @api.depends('name')
    def _compute_approval_purchase_id(self):
        for rec in self:
            rec.approval_purchase_id = self.env['dsn.approval.purchase'].search([('models', '=', 'purchase_request')], limit=1).id
                
class DsnPurchaseRequestApprovalLine(models.Model):
    _name = 'dsn.purchase.request.approval.line'
    _description = "DSN Purchase Request Approval Line"

    purchase_request_id = fields.Many2one('purchase.request', string="Purchase Request")
    is_approved = fields.Boolean(string="Is Approved")
    date_approved = fields.Datetime(string="Date Approved")
    user_id = fields.Many2one('res.users', string="User")
    signature = fields.Binary(related='user_id.employee_id.signature', string="Signature")