import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.tools import populate
from odoo.exceptions import ValidationError

#  =================================\approval line\========================================>
class DsnAccountMoveApprovalLine(models.Model):
    _name = 'dsn.account.move.approval.line'
    _description = "DSN Account Move Approval Line"

    account_move_id = fields.Many2one('account.move', string="Account Move")
    is_approved = fields.Boolean(string="Is Approved")
    date_approved = fields.Datetime(string="Date Approved")
    user_id = fields.Many2one('res.users', string="User")
    signature = fields.Binary(related='user_id.employee_id.signature', string="Signature")

class AccountMove(models.Model):
    _inherit = "account.move"

    approval_line_ids = fields.One2many('dsn.account.move.approval.line', 'account_move_id', string="Approval Line", )
    approval_accounting_id = fields.Many2one('dsn.approval.accounting', string="Approver Accounting", compute="_compute_approval_accounting_id")
    approval_rule = fields.Selection(related="approval_accounting_id.approval_rule", string="Approval Rule")
    approval_type = fields.Selection(related="approval_accounting_id.approval_type", string="Approval Type")
    models = fields.Selection(related="approval_accounting_id.models", string="Model")
    from_approval = fields.Boolean(string="Is from approval?", default=False)
    reset_from_approval = fields.Boolean(string="Reset Approval?",  default=False)
    
    state_entry = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('to_approve', 'Waiting Approval'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default='draft',
    )
    assigned_to_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approver",
    )
    user_in_assigned_to = fields.Boolean(string="User Is Assigned", compute="_computed_user_in_assigned_to")

    def _computed_user_in_assigned_to(self):
        if self.assigned_to_ids and self.state_entry == 'to_approve':
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
    def _compute_approval_accounting_id(self):
        for rec in self:
            rec.approval_accounting_id = self.env['dsn.approval.accounting'].search([('models', '=', rec.move_type)], limit=1).id

    def request_approval(self):
        records = []
        if self.user_id.sudo().employee_id.approver_ids:
            for appr_line in self.approval_accounting_id:
                if appr_line.approval_type == 'position-base-approval':
                    for job in appr_line.job_ids:
                        for approver in self.user_id.employee_id.approver_ids:
                            if job.job_id.id == approver.job_id.id:
                                records.append(approver.user_id.id)
                                self.env['dsn.account.move.approval.line'].create({
                                    'account_move_id': self.id,
                                    'user_id': approver.user_id.id,
                                })
                else:
                    for user in appr_line.user_ids:
                        records.append(user.user_id.id)
                        self.env['dsn.account.move.approval.line'].create({
                                'account_move_id': self.id,
                                'user_id': user.user_id.id,
                            })
                        
        if not self.user_id.sudo().employee_id.approver_ids or len(records) == 0:
            raise ValidationError(_("Can't find approver for current user!"))

        self.assigned_to_ids = [(6, 0, records)]

        # send notification 
        activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'account.move')], limit=1).id

        if self.approval_rule == 'only-one-approved':
            # send notification to the first approver
            for rec in records:
                self.send_mail_activity(activity_type_id, rec, self.id, res_model_id)
        else:
            # send notification to all approver
            self.send_mail_activity(activity_type_id, records[0], self.id, res_model_id)

        self.write({
                'state_entry': 'to_approve',
                "from_approval": True
            })
    
    def send_mail_activity(self, activity_type_id, user_id, res_id, res_model_id):
        self.env["mail.activity"].sudo().create(
            {
                "activity_type_id": activity_type_id,
                "note": _(
                    "You have items in the Vendor Pricelist document that you need to approve "
                    "Check if an action is needed."
                ),
                "user_id": (
                    user_id
                ),
                "res_id": res_id,
                "res_model_id": res_model_id,
                'summary': 'Reminder Vendor Pricelist Approval',
            }
        )

    def button_approve(self):
        approval_account_move = self.env['dsn.account.move.approval.line']
        # set is approved
        record = approval_account_move.search([('account_move_id', '=', self.id), ('user_id', '=', self.env.user.id), ('is_approved', '=', False)], limit=1)
        record.write({'is_approved': True, 'date_approved': datetime.now()})
        
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'account.move')], limit=1).id

        # set state
        if self.approval_rule == 'only-one-approved':
            # self.active_approver = self.assigned_to_ids
            if any(self.approval_line_ids.mapped('is_approved')):
                self.write({
                    "state_entry": "posted",
                }) 
                # set all mail activity to be done
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).action_done()
                # post
                self.action_post()
        # set state
        else:
            is_approved_counted = len(approval_account_move.search([('is_approved', '=', True), ('account_move_id.models', '=', self.move_type), ('account_move_id', '=', self.id)]).ids)
            approval_account_move_user = [rec.user_id for rec in approval_account_move.search([], order='id asc')]
            current_user_id = approval_account_move_user[is_approved_counted - 1] if is_approved_counted else approval_account_move_user[0]

            if all(self.approval_line_ids.mapped('is_approved')):
                self.write({
                    "state_entry": "posted",
                }) 
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                # post
                self.action_post()
            else:
                # assign to the next approver
                user_id = approval_account_move_user[is_approved_counted]

                # set mail activity to be done one by one
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
                
                # send notification to the next approver
                self.send_mail_activity(activity_type_id, user_id.id, self.id, res_model_id)
    
    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        # set state_entry to cancel
        self.write({'state_entry': 'cancel'})
        return res
    
    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        if self.from_approval:
            # set state_entry to draft
            self.write({
                'state_entry': 'draft',
                'from_approval': False
            })
            # ulink mail activity
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'account.move')], limit=1).id
            self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).unlink()
            # reset assigned_to_ids
            self.assigned_to_ids = [(6, 0, [])]
            # reset approval line
            self.env['dsn.account.move.approval.line'].search([('account_move_id', '=', self.id)]).unlink()
        else:
            self.write({'reset_from_approval':True})
        return res

