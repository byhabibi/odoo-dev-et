
from odoo import _, fields, models, api
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class DSNDemandPlanning(models.Model):
    _name = "dsn.demand.planning"
    _description = 'Demand Planning'
    _order = 'name'
    _inherit = ["mail.thread", "mail.activity.mixin"]


    name = fields.Char(default='New', tracking=True)
    start_date = fields.Date(default=lambda self: fields.Date.to_string(date.today().replace(day=1)), tracking=True)
    end_date = fields.Date(default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()), tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')], default='draft', tracking=True)
    line_ids = fields.One2many('dsn.demand.planning.line', 'demand_id')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny", default=lambda self: self.env.user.company_id, tracking=True)
    mrp_ids = fields.One2many('dsn.mrp', 'demand_id', string='MRP')
    mrp_count = fields.Integer(compute='_compute_mrp_count')

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

    def set_material(self, product, record, bom_line):
        for this in self:
            if this.state == 'done':
                raise ValidationError(_("Cannot set MRP with status %s.", this.state))

            bom_sfg = self.env['mrp.bom'].sudo().search([
                ('company_id', '=', this.company_id.id),
                ('active', '=', True),
                ('product_tmpl_id', '=', product.product_tmpl_id.id)], order='id desc',limit=1)
            if bom_sfg:
                continue

            else:
                qty_demand = record.production_qty * bom_line.product_qty
                qty_demand = self._get_calculate_qty(product.uom_po_id, bom_line.product_uom_id, qty_demand)

                free_qty = self._get_calculate_qty(product.uom_po_id, product.uom_id, product.free_qty)
                value = {
                    'bom_id': record.bom_id.id,
                    'uom_id': product.uom_po_id.id,
                    'company_id': this.company_id.id,
                    'demand_id': this.id,
                    'product_id': product.id,
                    'stock_on_hand': free_qty,
                    'demand_qty': qty_demand,
                    'deadline_date': record.deadline_date,
                }
                self.env['dsn.mrp'].create(value)

    def set_mrp(self):
        for this in self:
            for line in this.line_ids:
                if line.production_qty == 0:
                    continue

                if line.bom_type == 'subcontract':
                    qty_demand = line.production_qty
                    qty_demand = self._get_calculate_qty(line.product_id.uom_po_id, line.product_id.uom_id, qty_demand)

                    free_qty = self._get_calculate_qty(line.product_id.uom_po_id, line.product_id.uom_id, product.free_qty)
                    value = {
                        'bom_id': line.bom_id.id,
                        'uom_id': line.product_id.uom_po_id.id,
                        'company_id': line.company_id.id,
                        'demand_id': this.id,
                        'product_id': line.product_id.id,
                        'stock_on_hand': free_qty,
                        'demand_qty': qty_demand,
                        'deadline_date': line.deadline_date,
                    }
                    self.env['dsn.mrp'].create(value)
                for bom_line in line.bom_id.bom_line_ids:
                    product = bom_line.product_id
                    record = line
                    this.set_material(product, record, bom_line)

            this.write({'state': 'done'})
                    
    def view_mrp(self):
        view_tree = self.env.ref('mrp_forecast_order.dsn_view_mrp_tree').id
        action = {
            'name': 'MRP',
            'domain': [('id', 'in', self.mrp_ids.ids)],
            'view_mode': 'tree',
            'res_model': 'dsn.mrp',
            'views': [(view_tree, 'tree')],
            'type': 'ir.actions.act_window',
            'context': {'create':0, 'copy':0, 'delete':0}
        }

        return action

    def _compute_mrp_count(self):
        for this in self:
            this.mrp_count = len(this.mrp_ids.ids)

    def unlink(self):
        for this in self:
            if this.state != 'draft':
                raise ValidationError(_("Cannot delete with status %s.", this.state))
        return super(DSNDemandPlanning, self).unlink()

    def set_sfg(self, product, record, bom_line, line_level):
        for this in self:
            bom_sfg = self.env['mrp.bom'].sudo().search([
                ('company_id', '=', this.company_id.id),
                ('active', '=', True),
                ('product_tmpl_id', '=', product.product_tmpl_id.id)], order='id desc',limit=1)
            if bom_sfg:
                qty_demand = record.production_qty * bom_line.product_qty
                
                value = {
                    'level': line_level,
                    'uom_id': product.uom_id.id,
                    'company_id': this.company_id.id,
                    'demand_id': this.id,
                    'product_id': product.id,
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'stock_on_hand': product.free_qty,
                    'bom_id': bom_sfg.id or False,
                    'demand_qty': qty_demand,
                    'demand_line_id': record.id,
                    'note': 'SFG :' + ' ' + str(qty_demand),
                    'deadline_date': record.deadline_date,
                    
                }
                records = self.env['dsn.demand.planning.line'].create(value)
                records._compute_production_qty()
                add_level = 1
                for bom_line in bom_sfg.bom_line_ids:
                    level_line_add = line_level+'.'+str(add_level)
                    product = bom_line.product_id
                    record = records
                    this.set_sfg(product, record, bom_line, level_line_add)
                    add_level +=1

    def action_confirm(self):
        for this in self:
            level = 1
            for line in this.line_ids:
                if not line.bom_id:
                    raise ValidationError(_("Bill of Material in demand detail cannot be empty."))
                if not line.deadline_date:
                    raise ValidationError(_("Daedline date in demand detail cannot be empty."))
                
                for forecast in line.forecast_ids:
                    for line_forecast in forecast.forecast_line_ids.filtered(lambda x:x.product_id == line.product_id\
                        and x.forecast_date >= this.start_date and x.forecast_date <= this.end_date):
                        line_forecast.write({'is_demand_order': True})

                    not_demand_order = forecast.forecast_line_ids.filtered(lambda x:x.is_demand_order == False)
                    if not not_demand_order:
                        forecast.write({'state': 'done'}) 
                
                for bom_line in line.bom_id.bom_line_ids:
                    line_level = str(line.level) + '.' + str(level)
                    product = bom_line.product_id
                    record = line
                    this.set_sfg(product, record, bom_line, line_level)

                level += 1
            
            this.write({'state': 'in_progress'})

    def reset_to_draft(self):
        for this in self:
            for line in this.line_ids:
                if line.mps_ids:
                    raise ValidationError(_("can't reset to draft because there are already mps made of demand details."))

                for forecast in line.forecast_ids:
                    for line_forecast in forecast.forecast_line_ids:
                        line_forecast.write({'is_demand_order': False})

                    forecast.write({'state': 'confirm'})

            line_unlink = this.line_ids.filtered(lambda x:x.demand_line_id)
            if line_unlink:
                line_unlink.unlink()

            this.write({'state': 'draft'})

    def get_forecast_data(self):
        for this in self:
            product_forecast_list = self.env['dsn.forecast.order.line'].sudo().search([
                ('company_id', '=', this.company_id.id),
                ('forecast_id.state', '=', 'confirm'),
                ('is_demand_order', '=', False),
                ('forecast_date', '>=', this.start_date),
                ('forecast_date', '<=', this.end_date)]).mapped('product_id')  
            datas = []
            level = 1
            for product in product_forecast_list:
                forecast_line_list = self.env['dsn.forecast.order.line'].sudo().search([
                    ('company_id', '=', this.company_id.id),
                    ('forecast_id.state', '=', 'confirm'),
                    ('forecast_date', '>=', this.start_date),
                    ('forecast_date', '<=', this.end_date),
                    ('is_demand_order', '=', False),
                    ('product_id', '=', product.id)])
                bom = self.env['mrp.bom'].sudo().search([
                    ('company_id', '=', this.company_id.id),
                    ('active', '=', True),
                    ('product_tmpl_id', '=', product.product_tmpl_id.id)], order='id desc', limit=1)

                value = {
                    'company_id': this.company_id.id,
                    'level': str(level),
                    'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'stock_on_hand': product.free_qty,
                    'bom_id': bom.id or False,
                    'demand_qty': sum(forecast_line_list.mapped('quantity')),
                    'forecast_ids': forecast_line_list.mapped('forecast_id').ids,
                    'note': 'Forecast :' + ' ' + str(sum(forecast_line_list.mapped('quantity'))) 
                }
                level += 1
                datas.append((0,0, value))

            this.line_ids = [(5,)]
            this.line_ids = datas

    def get_sale_demand(self):
        for this in self:
            product_sale_order_line = self.env['sale.order.line'].sudo().search([
                ('company_id', '=', this.company_id.id),
                ('order_id.state', '=', 'sale'),
                ('order_id.date_order', '>=', this.start_date),
                ('order_id.date_order', '<=', this.end_date)]).mapped('product_id')
            
            level = len(this.line_ids) + 1
            for product in product_sale_order_line:
                qty_demand = 0
                sale_order_list = []
                if product.detailed_type == 'product':
                    sale_order_line = self.env['sale.order.line'].sudo().search([
                        ('product_id', '=', product.id),
                        ('company_id', '=', this.company_id.id),
                        ('order_id.state', '=', 'sale'),
                        ('order_id.date_order', '>=', this.start_date),
                        ('order_id.date_order', '<=', this.end_date)])
                    for line in sale_order_line:
                        if line.qty_delivered < line.product_uom_qty:
                            qty_demand += line.product_uom_qty - line.qty_delivered
                            sale_order_list.append(line.order_id.id)

                    if qty_demand > 0:
                        product_exist_in_line = this.line_ids.filtered(lambda x: x.product_id == product)

                        if product_exist_in_line:
                            product_exist_in_line.write({
                                'demand_qty': product_exist_in_line.demand_qty + qty_demand,
                                'sale_order_ids': sale_order_line.mapped('order_id').ids,
                                'note': product_exist_in_line.note + ', ' + 'Sale :' + ' ' + str(qty_demand)
                            })
                        else:
                            for line in sale_order_line:
                                sale_order_list.append(line.order_id.id)
        
                            bom = self.env['mrp.bom'].sudo().search([
                                ('company_id', '=', this.company_id.id),
                                ('active', '=', True),
                                ('product_tmpl_id', '=', product.product_tmpl_id.id)], order='id desc', limit=1)
                            
                            value = {
                                'level': str(level),
                                'company_id': this.company_id.id,
                                'demand_id': this.id,
                                'product_id': product.id,
                                'product_tmpl_id': product.product_tmpl_id.id,
                                'stock_on_hand': product.free_qty,
                                'bom_id': bom.id or False,
                                'uom_id': product.uom_id.id,
                                'demand_qty': qty_demand,
                                'sale_order_ids':  sale_order_list,
                                'note': 'Sale :' + ' ' + str(qty_demand)
                            }
                            level += 1
                            self.env['dsn.demand.planning.line'].create(value)

    def search_data(self):
        for this in self:
            this.get_forecast_data()
            this.get_sale_demand()

    def replace_name(self):
        for this in self:
            this.name = self.env['ir.sequence'].next_by_code('dsn.demand')

    @api.model
    def create(self, vals):
        res = super(DSNDemandPlanning, self).create(vals)
        res.replace_name()
        return res

    @api.constrains('start_date', 'end_date')
    def constrains_date(self):
        for this in self:
            if this.start_date > this.end_date:
                raise ValidationError(_('Start date cannot be greater than end date.'))


class DSNDemandPlanningLine(models.Model):
    _name = "dsn.demand.planning.line"
    _description = 'Demand Planning Line'
    _rec_name = 'product_id'
    _order = 'level asc'
    _inherit = ["mail.thread", "mail.activity.mixin"]


    demand_id = fields.Many2one('dsn.demand.planning', ondelete='cascade', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    level = fields.Char(tracking=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', tracking=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', tracking=True)
    buffer_stock = fields.Float(string='Buffer Stock', tracking=True, compute='compute_buffer_stock')
    stock_on_hand = fields.Float(string='Initial Available', tracking=True)
    demand_qty = fields.Float(string='Demand Qty', tracking=True)
    fulfilled_qty = fields.Float(string='Fulfilled Qty', tracking=True, compute='_compute_production_qty')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny", related='demand_id.company_id', tracking=True)
    forecast_ids = fields.Many2many('dsn.forecast.order', string='Forecast')
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', tracking=True)
    deadline_date = fields.Date(tracking=True)
    note = fields.Char(tracking=True)
    sale_order_ids = fields.Many2many('sale.order', string='Sale Order', tracking=True)
    demand_line_id = fields.Many2one('dsn.demand.planning.line', string='Parent', tracking=True)
    bom_type = fields.Selection(related='bom_id.type', tracking=True)
    production_qty = fields.Float(string='Production Qty', compute='_compute_production_qty')
    mps_ids = fields.One2many('dsn.mps', 'demand_line_id')
    mps_qty = fields.Float(string='MPS Qty', compute='_compute_mps')


    @api.depends('mps_ids')
    def _compute_mps(self):
        for this in self:
            this.mps_qty = sum(this.mps_ids.mapped('production_qty'))

    @api.constrains('mps_qty')
    def _constrains_mps_qty(self):
        for this in self:
            if this.mps_qty > this.production_qty:
                raise ValidationError(_('MPS Qty cannot be greater than production qty for product %s', this.product_id.display_name))
                
    def compute_buffer_stock(self):
        for this in self:
            buffer_stock = self.env['stock.warehouse.orderpoint'].sudo().search([
                    ('product_id', '=', this.product_id.id),
                    ('company_id', '=', this.company_id.id)])
            this.buffer_stock = sum(buffer_stock.mapped('product_min_qty'))

    def _compute_production_qty(self):
        for this in self:
            if not this.demand_line_id:
                production_qty = this.demand_qty - this.stock_on_hand + this.buffer_stock
            if this.demand_line_id:
                bom_qty_line = this.demand_line_id.bom_id.bom_line_ids.filtered(lambda x: x.product_id == this.product_id).product_qty
                demand_real = this.demand_line_id.production_qty * bom_qty_line
                production_qty = demand_real - this.stock_on_hand + this.buffer_stock
            if production_qty < 0:
                production_qty = 0
            this.production_qty = production_qty

            mo_done = [0]
            for mps in this.mps_ids:
                for mo in mps.mo_ids:
                    if mo.state == 'done':
                        mo_done.append(mo.qty_producing)
            this.fulfilled_qty = sum(mo_done)

    def create_buffer_stock(self):
        for this in self:
            view_form = self.env.ref('mrp_forecast_order.dsn_view_warehouse_orderpoint_form').id
            route = self.env.ref('mrp.route_warehouse0_manufacture').id
            action = {
                'name': 'Replenishment',
                'domain': [],
                'view_mode': 'form',
                'res_model': 'stock.warehouse.orderpoint',
                'views': [(view_form, 'form')],
                'type': 'ir.actions.act_window',
                'context': {
                    'default_product_id': this.product_id.id,
                    'deafault_active': True,
                    'default_route_id': route,
                }
            }

            return action
        
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
        
    def generate_mps(self):
        if not self.deadline_date:
             raise ValidationError(_("Daedline date cannot be empty."))
        if self.production_qty == self.mps_qty:
             raise ValidationError(_("Production quantity has been met by the quanity of mps."))
        action = self.env['ir.actions.actions']._for_xml_id('mrp_forecast_order.dsn_action_mps_wizard')
        return action

    def view_mps(self):
        for this in self:
            view_tree = self.env.ref('mrp_forecast_order.dsn_view_mps_tree').id
            action = {
                'name': 'MPS',
                'domain': [('id', 'in', this.mps_ids.ids)],
                'view_mode': 'tree',
                'res_model': 'dsn.mps',
                'views': [(view_tree, 'tree')],
                'type': 'ir.actions.act_window',
                'context': {'edit': 0, 'create':0, 'copy':0, 'delete':0}
            }

            return action