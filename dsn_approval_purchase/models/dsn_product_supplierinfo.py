import logging
from datetime import datetime
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.tools import populate
from odoo.exceptions import ValidationError

class ProductSupplierinfo(models.Model):
    _name = "product.supplierinfo"
    _inherit = ['product.supplierinfo','portal.mixin', 'mail.thread', 'mail.activity.mixin']

    approval_line_ids = fields.One2many('dsn.product.supplierinfo.approval.line', 'vendor_pricelist_id', string="Approval Line", copy=False)
    approval_purchase_id = fields.Many2one('dsn.approval.purchase', string="Approver Purchase", compute="_compute_approval_purchase_id")
    approval_rule = fields.Selection(related="approval_purchase_id.approval_rule", string="Approval Rule", copy=False)
    approval_type = fields.Selection(related="approval_purchase_id.approval_type", string="Approval Type", copy=False)
    assigned_to_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approver", copy=False
    )
    models = fields.Selection(related="approval_purchase_id.models", string="Model")
    date_start = fields.Date('Start Date', help="Start date for this vendor price",required=True, copy=False, default=fields.Date.today())
    date_end = fields.Date('End Date', help="End date for this vendor price",required=True, copy=False, default=fields.Date.today())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Approval'),
        ('done', 'Done'),
    ], string="State", default='draft', tracking=True, copy=False, )
    user_in_assigned_to = fields.Boolean(string="User Is Assigned", compute="_computed_user_in_assigned_to")

    def get_date_list(self, start_date, end_date):
        start = datetime.strptime(str(start_date), '%Y-%m-%d')
        end = datetime.strptime(str(end_date), '%Y-%m-%d')

        date_list = []
        current_date = start
        while current_date <= end:
            date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        return date_list

    @api.constrains('date_start')
    def _constrains_date_start(self):
        for pricelist in self.search([('product_tmpl_id',  '=', self.product_tmpl_id.id), ('partner_id', '=', self.partner_id.id), ('id', '!=' ,self.id)]):
            if pricelist.date_start and pricelist.date_end:
                # current record
                self_date_list = self.get_date_list(self.date_start, self.date_end)
                # another record
                pricelist_date_list = self.get_date_list(pricelist.date_start, pricelist.date_end)

                for date in self_date_list:
                    if date in pricelist_date_list:
                        if not pricelist.product_tmpl_id:
                            continue
                        raise ValidationError(_("The validity date for Vendor Pricelist with vendor %s and product %s overlaps with other records.", self.partner_id.name, self.product_tmpl_id.name))

    @api.constrains('date_end')
    def _constrains_date_end(self):
        for pricelist in self.search([('product_tmpl_id', '=', self.product_tmpl_id.id), ('partner_id', '=', self.partner_id.id), ('id', '!=' ,self.id)]):
            if pricelist.date_start and pricelist.date_end:
                # current record
                self_date_list = self.get_date_list(self.date_start, self.date_end)
                # another record
                pricelist_date_list = self.get_date_list(pricelist.date_start, pricelist.date_end)

                for date in self_date_list:
                    if date in pricelist_date_list:
                        if not pricelist.product_tmpl_id:
                            continue
                        raise ValidationError(_("The validity date for Vendor Pricelist with vendor %s and product %s overlaps with other records.", self.partner_id.name, self.product_tmpl_id.name))
    
    def _computed_user_in_assigned_to(self):
        if self.assigned_to_ids and self.state == 'waiting':
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

    def request_approval(self):
        records = []
        if self.env.user.sudo().employee_id.approver_ids:
            for appr_line in self.approval_purchase_id:
                if appr_line.approval_type == 'position-base-approval':
                    for job in appr_line.job_ids:
                        if not self.env.user.sudo().employee_id.approver_ids:
                            raise ValidationError(_("Can't find approver for current user!"))
                        for approver in self.env.user.sudo().employee_id.approver_ids:
                            if job.job_id.id == approver.job_id.id:
                                records.append(approver.user_id.id)
                                self.env['dsn.product.supplierinfo.approval.line'].create({
                                    'vendor_pricelist_id': self.id,
                                    'user_id': approver.user_id.id,
                                })
                else:
                    for user in appr_line.user_ids:
                        records.append(user.user_id.id)
                        self.env['dsn.product.supplierinfo.approval.line'].create({
                                'vendor_pricelist_id': self.id,
                                'user_id': user.user_id.id,
                            })
        if len(records) == 0:
            raise ValidationError(_("Can't find approver for current user!"))


        self.assigned_to_ids = [(6, 0, records)]

        # send notification 
        activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'product.supplierinfo')], limit=1).id

        if self.approval_rule == 'only-one-approved':
            # send notification to the first approver
            for rec in records:
                self.send_mail_activity(activity_type_id, rec, self.id, res_model_id)
        else:
            # send notification to all approver
            self.send_mail_activity(activity_type_id, records[0], self.id, res_model_id)

        self.write({'state': 'waiting'})
    
    def reset_to_draft(self):
        # ulink mail activity
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'product.supplierinfo')], limit=1).id
        self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).unlink()
        # reset assigned_to_ids
        self.assigned_to_ids = [(6, 0, [])]
        # reset approval line
        self.env['dsn.product.supplierinfo.approval.line'].search([('vendor_pricelist_id', '=', self.id)]).unlink()
        self.write({'state': 'draft'})

    def button_approve(self):
        approval_vendor_pricelist = self.env['dsn.product.supplierinfo.approval.line']
        # set is approved
        record = approval_vendor_pricelist.search([('vendor_pricelist_id', '=', self.id), ('user_id', '=', self.env.user.id), ('is_approved', '=', False)], limit=1)
        record.write({'is_approved': True, 'date_approved': datetime.now()})
        
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'product.supplierinfo')], limit=1).id

        # set state
        if self.approval_rule == 'only-one-approved':
            # self.active_approver = self.assigned_to_ids
            if any(self.approval_line_ids.mapped('is_approved')):
                self.write({"state": "done"}) 
                # set all mail activity to be done
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).action_done()
        # set state
        else:
            is_approved_counted = len(approval_vendor_pricelist.search([('is_approved', '=', True), ('vendor_pricelist_id.models', '=', 'vendor_pricelist'), ('vendor_pricelist_id', '=', self.id)]).ids)
            approval_vendor_pricelist_user = [rec.user_id for rec in approval_vendor_pricelist.search([], order='id asc')]
            current_user_id = approval_vendor_pricelist_user[is_approved_counted - 1] if is_approved_counted else approval_vendor_pricelist_user[0]

            if all(self.approval_line_ids.mapped('is_approved')):
                self.write({"state": "done"}) 
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
            else:
                # assign to the next approver
                user_id = approval_vendor_pricelist_user[is_approved_counted]

                # set mail activity to be done one by one
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
                
                # send notification to the next approver
                self.send_mail_activity(activity_type_id, user_id.id, self.id, res_model_id)

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
    @api.depends('partner_id')
    def _compute_approval_purchase_id(self):
        for rec in self:
            rec.approval_purchase_id = self.env['dsn.approval.purchase'].search([('models', '=', 'vendor_pricelist')], limit=1).id

class DsnProductSupplerinfoApprovalLine(models.Model):
    _name = 'dsn.product.supplierinfo.approval.line'
    _description = "DSN Product Supplierinfo Approval Line"

    vendor_pricelist_id = fields.Many2one('product.supplierinfo', string="Vendor Pricelist")
    is_approved = fields.Boolean(string="Is Approved")
    date_approved = fields.Datetime(string="Date Approved")
    user_id = fields.Many2one('res.users', string="User")
    signature = fields.Binary(related='user_id.employee_id.signature', string="Signature")
