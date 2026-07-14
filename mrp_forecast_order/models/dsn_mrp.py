
from odoo import _, fields, models, api
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class DSNMRP(models.Model):
    _name = 'dsn.mrp'
    _description = 'MRP'
    _inherit = ["mail.thread", "mail.activity.mixin"]


    name = fields.Char()
    demand_id = fields.Many2one('dsn.demand.planning', ondelete='cascade', tracking=True)
    product_id = fields.Many2one('product.product', string='Product')
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material Ref.', tracking=True)
    uom_id = fields.Many2one('uom.uom', string='Purchase UoM', related=False, store=True)
    mrp_buffer_stock = fields.Float(string='Buffer Stock', tracking=True, compute='compute_buffer_stock')
    stock_on_hand = fields.Float(string='Initial Available', tracking=True)
    demand_qty = fields.Float(string='Demand Qty', tracking=True)
    deadline_date = fields.Date(tracking=True)
    quantity_to_buy = fields.Float(string='Quantity to Buy', compute='compute_quantity_purchase')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny", default=lambda self: self.env.user.company_id, tracking=True)
    purchase_request_line_ids = fields.One2many('purchase.request.line', 'mrp_id', string='Purchase Request Line')
    purchase_request_line_id = fields.Many2one('purchase.request.line', string='Purchase Request Line')
    quantity_pr = fields.Float(string='Qty PR', compute='compute_quantity_purchase')
    quantity_po = fields.Float(string='Qty PO', compute='compute_quantity_purchase')
    received_qty = fields.Float(string='Qty Received', compute='compute_balance')
    balance = fields.Float(string='Balance', compute='compute_balance', store=True)


    def _get_calculate_qty(self, uom_po, uom_id, quantity):
        if uom_po.id != uom_id.id:
            if uom_po.uom_type == 'bigger':
                qty_calculate =quantity * uom_po.factor
                return qty_calculate
            elif uom_po.uom_type == 'smaller':
                qty_calculate =quantity * uom_po.factor
                return qty_calculate
            elif uom_id.uom_type == 'bigger':
                qty_calculate =quantity / uom_id.factor
                return qty_calculate
            elif uom_id.uom_type == 'smaller':
                qty_calculate =quantity / uom_id.factor
                return qty_calculate
            else:
                qty_calculate =quantity
                return qty_calculate
        else:
            qty_calculate =quantity
            return qty_calculate

    def compute_buffer_stock(self):
        for this in self:
            buffer_stock = self.env['stock.warehouse.orderpoint'].sudo().search([
                    ('product_id', '=', this.product_id.id),
                    ('company_id', '=', this.company_id.id)])
            
            buffer_list = []
            for buf in buffer_stock:
                buffer_stock = self._get_calculate_qty(buf.product_id.uom_po_id, buf.product_id.uom_id, buf.product_min_qty)
                buffer_list.append(buffer_stock)
    
            this.mrp_buffer_stock = sum(buffer_list)

    def compute_balance(self):
        for this in self:
            received_lines = []
            purchase_line = self.env['purchase.request.line'].sudo().search([
                ('product_id', '=', this.product_id.id),
                ('company_id', '=', this.company_id.id),
                ('mrp_id', '=', this.id)
            ])
            for pr_line in purchase_line:
                for pr in pr_line.purchase_lines:
                    received_lines.append(pr.qty_received)

            balance = this.demand_qty - sum(received_lines)
            if balance < 0:
                balance = 0
            this.balance = balance
            this.received_qty = sum(received_lines)

    def compute_quantity_purchase(self):
        for this in self:
            quantity_to_buy = this.demand_qty - this.stock_on_hand + this.mrp_buffer_stock - this.quantity_pr
            if quantity_to_buy < 0:
                quantity_to_buy = 0

            this.quantity_to_buy = quantity_to_buy

            quantity_pr_line = self.env['purchase.request.line'].sudo().search([
                ('product_id', '=', this.product_id.id),
                ('company_id', '=', this.company_id.id),
                ('mrp_id', '=', this.id),
                ('request_id.state', 'not in', ('rejected', 'done'))])
            this.quantity_pr = sum(quantity_pr_line.mapped('product_qty'))
            this.quantity_po =  sum(quantity_pr_line.mapped('purchased_qty'))  

    def replace_name(self):
        for this in self:
            this.name = self.env['ir.sequence'].next_by_code('dsn.mrp')

    @api.model
    def create(self, vals):
        res = super(DSNMRP, self).create(vals)
        res.replace_name()
        return res

    def view_buffer_stock(self):
        for this in self:
            view_tree = self.env.ref('stock.view_warehouse_orderpoint_tree_editable').id
            action = {
                'name': 'Replenishment',
                'domain': [('product_id', '=', this.product_id.id), ('company_id', '=', this.company_id.id)],
                'view_mode': 'tree',
                'res_model': 'stock.warehouse.orderpoint',
                'views': [(view_tree, 'tree')],
                'type': 'ir.actions.act_window',
                'context': {'edit': 0, 'create':0, 'copy':0, 'delete':0}
            }
            return action
        
    def view_pr(self):
        for this in self:
            view_tree = self.env.ref('purchase_request.purchase_request_line_tree').id
            action = {
                'name': 'Purchase Request Lines',
                'domain': [('product_id', '=', this.product_id.id), ('company_id', '=', this.company_id.id),('mrp_id', '=', this.id)],
                'view_mode': 'tree',
                'res_model': 'purchase.request.line',
                'views': [(view_tree, 'tree')],
                'type': 'ir.actions.act_window',
                'context': {'edit': 0, 'create':0, 'copy':0, 'delete':0}
            }
            return action
        
    
    def view_po(self):
        for this in self:
            view_tree = self.env.ref('purchase.purchase_order_line_tree').id
            purchase_lines = []
            purchase_line = self.env['purchase.request.line'].sudo().search([
                ('product_id', '=', this.product_id.id),
                ('company_id', '=', this.company_id.id),
                ('mrp_id', '=', this.id)
            ])
            for pr_line in purchase_line:
                for pr in pr_line.purchase_lines:
                    purchase_lines.append(pr.id)
            
            action = {
                'name': 'Purchase',
                'domain': [('id', 'in', purchase_lines)],
                'view_mode': 'tree',
                'res_model': 'purchase.order.line',
                'views': [(view_tree, 'tree')],
                'type': 'ir.actions.act_window',
                'context': {'edit': 0, 'create':0, 'copy':0, 'delete':0}
            }
            return action

    def create_buffer_stock(self):
        for this in self:
            view_form = self.env.ref('mrp_forecast_order.dsn_view_warehouse_orderpoint_form').id
            route = self.env.ref('purchase_stock.route_warehouse0_buy').id
            action = {
                'name': 'Replenishment',
                'domain': [],
                'view_mode': 'form',
                'res_model': 'stock.warehouse.orderpoint',
                'views': [(view_form, 'form')],
                'type': 'ir.actions.act_window',
                'context': {
                    'default_product_id': this.product_id.id,
                    'default_active': True,
                    'default_route_id': route,
                }
            }

            return action

    def create_pr(self):
         for this in self:
            if this.quantity_to_buy == 0:
                raise ValidationError(_("Quantity to buy has been met by the quanity of Purchase Request."))
            
            if this.purchase_request_line_id:
                raise ValidationError(_("Purchase request has already been made, so you can't make a purchase request again."))

            picking_type = self.env['stock.picking.type'].sudo().search([
                ('company_id', '=', this.company_id.id),
                ('code', '=', 'incoming')], limit=1)

            line_ids = [(0,0,{
                'product_id': this.product_id.id,
                'product_qty': this.quantity_to_buy - this.quantity_pr,
                'product_uom_id': this.uom_id.id,
                'mrp_id': this.id,
            })]

            pr = self.env['purchase.request'].sudo().create({
                'requested_by': self.env.user.id,
                'company_id': this.company_id.id,
                'date_start': fields.date.today(),
                'picking_type_id': picking_type.id or False,
                'line_ids': line_ids,
                'origin': this.name})

            for pr_line in pr.line_ids:
                pr_line.name = str(pr.name) + ' ' + str(pr_line.product_id.display_name)

    def merge_create_pr(self):
        for this in self:
            if this.quantity_to_buy == 0:
                raise ValidationError(_('%s, quantity already fulfilled.', this.name))
            
            if this.purchase_request_line_id:
                raise ValidationError(_('%s, purchase request already made.', this.name))

        action = self.env['ir.actions.actions']._for_xml_id('mrp_forecast_order.dsn_action_mrp_wizard')
        return action


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'


    mrp_id = fields.Many2one('dsn.mrp', string='MRP')