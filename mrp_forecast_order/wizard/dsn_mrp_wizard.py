from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import mimetypes
import base64
import itertools
import math
import logging
_logger = logging.getLogger(__name__)


class DSNMRPWizard(models.TransientModel):
    _name = 'dsn.mrp.wizard'
    _description = 'DSN MRP Wizard'


    def get_line(self):
        context = self._context
        active_ids = context.get('active_ids')
        datas = []
        products = self.env['dsn.mrp'].search([('id', 'in', active_ids)]).mapped('product_id').ids
        for prod in products:
            mrp_by_prod = self.env['dsn.mrp'].search([('id', 'in', active_ids), ('product_id', '=', prod)])
            quantity = sum(mrp_by_prod.mapped('quantity_to_buy'))
            value = {
                'mrp_ids': mrp_by_prod.ids,
                'product_id': prod,
                'product_qty': math.ceil(quantity),
                'uom_id': mrp_by_prod[0].uom_id.id,
            }
        
            datas.append((0,0, value))

        return datas


    line_ids = fields.One2many('dsn.mrp.line.wizard', 'wizard_id', default=get_line)


    def create_purchase_request(self):
        line_ids = []
        origin_list = []
        for line in self.line_ids:
            value = {
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'product_uom_id': line.uom_id.id,
            }
            line_ids.append((0,0, value))
            origin_list.append(line.mrp_id.name)

        if self.line_ids:
            picking_type = self.env['stock.picking.type'].sudo().search([
                ('company_id', '=', self.env.company.id),
                ('code', '=', 'incoming')], limit=1)
            
            pr = self.env['purchase.request'].sudo().create({
                'requested_by': self.env.user.id,
                'company_id': self.env.company.id,
                'date_start': fields.date.today(),
                'picking_type_id': picking_type.id or False,
                'line_ids': line_ids,
                'origin': ', '.join(origin_list)})

            for pr_line in pr.line_ids:
                pr_line.name = str(pr.name) + ' ' + str(pr_line.product_id.display_name)

            for line in self.line_ids:
                for mrp in line.mrp_ids:
                    mrp.write({'purchase_request_ids': [(6, 0, [pr.id])]})
                    _logger.info(mrp.purchase_request_ids)


class DSNMRPLineWizard(models.TransientModel):
    _name = 'dsn.mrp.line.wizard'
    _description = 'DSN MRP Line Wizard'


    wizard_id = fields.Many2one('dsn.mrp.wizard', ondelete='cascade')
    mrp_id = fields.Many2one('dsn.mrp', string='MRP')
    mrp_ids = fields.Many2many('dsn.mrp', string='MRP')
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float('Quantity')
    uom_id = fields.Many2one('uom.uom', string='UoM')