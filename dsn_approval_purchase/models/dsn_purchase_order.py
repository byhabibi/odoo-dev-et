import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.tools import populate
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    is_approved = fields.Boolean('Is Approve', copy=False)
    approval_line_ids = fields.One2many('dsn.purchase.order.approval.line', 'purchase_order_id', string="Approval Line", copy=False)
    approval_purchase_id = fields.Many2one('dsn.approval.purchase', string="Approver Purchase", compute="_compute_approval_purchase_id")
    approval_rule = fields.Selection(related="approval_purchase_id.approval_rule", string="Approval Rule", copy=False)
    approval_type = fields.Selection(related="approval_purchase_id.approval_type", string="Approval Type", copy=False)
    models = fields.Selection(related="approval_purchase_id.models", string="Model")
    

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', tracking=True, copy=False, )

    assigned_to_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approver", copy=False
    )
    user_in_assigned_to = fields.Boolean(string="User Is Assigned", compute="_computed_user_in_assigned_to")
    

    def button_confirm_to_approve(self):
        self.write({'state': 'to approve'})

    
    def dsn_button_approve(self):
        approval_purchase_order = self.env['dsn.purchase.order.approval.line']
        # set is approved
        record = approval_purchase_order.search([('purchase_order_id', '=', self.id), ('user_id', '=', self.env.user.id),('is_approved', '=', False)], limit=1)
        record.write({'is_approved': True, 'date_approved': datetime.now()})
        
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')], limit=1).id

        # set state
        if self.approval_rule == 'only-one-approved':
            # self.active_approver = self.assigned_to_ids
            if any(self.approval_line_ids.mapped('is_approved')):
                self.write({'is_approved': True}) 
                # set all mail activity to be done
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).action_done()
                # confirm order
                self.button_confirm()
        # set state
        else:
            is_approved_counted = len(approval_purchase_order.search([('is_approved', '=', True), ('purchase_order_id.models', '=', 'purchase_order'), ('purchase_order_id', '=', self.id)]).ids)
            # approval_purchase_order_user = [rec.user_id for rec in approval_purchase_order.search([], order='id asc')]
            # current_user_id = approval_purchase_order_user[is_approved_counted - 1] if is_approved_counted else approval_purchase_order_user[0]
            current_user = self.approval_line_ids[is_approved_counted - 1]  if is_approved_counted else self.approval_line_ids[is_approved_counted - 1]
            current_user_id = current_user.user_id

            if all(self.approval_line_ids.mapped('is_approved')):
                self.write({'is_approved': True}) 
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                # confirm order
                self.button_confirm()
            else:
                # assign to the next approver
                # user_id = approval_purchase_order_user[is_approved_counted]
                user_id = self.approval_line_ids[is_approved_counted]

                # set mail activity to be done one by one
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
                
                # send notification to the next approver
                self.send_mail_activity(activity_type_id, user_id.user_id.id, self.id, res_model_id)
        
    def button_cancel(self):
        res = super(PurchaseOrder, self).button_cancel()
        # ulink mail activity
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')], limit=1).id
        self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).unlink()
        # reset assigned_to_ids
        self.assigned_to_ids = [(6, 0, [])]
        # reset approval line
        self.env['dsn.purchase.order.approval.line'].search([('purchase_order_id', '=', self.id)]).unlink()
        # reset is approved to be False
        self.write({'is_approved': False}) 
        return res
    
    def request_approval(self):
        records = []
    
        if self.user_id.sudo().employee_id.approver_ids:
            for appr_line in self.approval_purchase_id:
                if appr_line.approval_type == 'position-base-approval':
                    for job in appr_line.job_ids:
                        for approver in self.user_id.employee_id.approver_ids:
                            if job.job_id.id == approver.job_id.id:
                                records.append(approver.user_id.id)
                                self.env['dsn.purchase.order.approval.line'].create({
                                    'purchase_order_id': self.id,
                                    'user_id': approver.user_id.id,
                                })
                else:
                    for user in appr_line.user_ids:
                        records.append(user.user_id.id)
                        self.env['dsn.purchase.order.approval.line'].create({
                                'purchase_order_id': self.id,
                                'user_id': user.user_id.id,
                            })
                        
        if not self.user_id.sudo().employee_id.approver_ids or len(records) == 0:
            raise ValidationError(_("Can't find approver for current user!"))

        self.assigned_to_ids = [(6, 0, records)]

        # send notification 
        activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')], limit=1).id

        if self.approval_rule == 'only-one-approved':
            # send notification to the first approver
            for rec in records:
                self.send_mail_activity(activity_type_id, rec, self.id, res_model_id)
        else:
            # send notification to all approver
            self.send_mail_activity(activity_type_id, records[0], self.id, res_model_id)

        self.write({'state': 'to approve'})
    
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

    def _computed_user_in_assigned_to(self):
        if self.assigned_to_ids and self.state == 'to approve':
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
    
    @api.depends('name')
    def _compute_approval_purchase_id(self):
        for rec in self:
            rec.approval_purchase_id = self.env['dsn.approval.purchase'].search([('models', '=', 'purchase_order')], limit=1).id

class DsnPurchaseOrderApprovalLine(models.Model):
    _name = 'dsn.purchase.order.approval.line'
    _description = "DSN Purchase Order Approval Line"

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    is_approved = fields.Boolean(string="Is Approved")
    date_approved = fields.Datetime(string="Date Approved")
    user_id = fields.Many2one('res.users', string="User")
    signature = fields.Binary(related='user_id.employee_id.signature', string="Signature")