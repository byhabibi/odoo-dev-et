from odoo import _, fields, models, api, Command
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
import logging
_logger = logging.getLogger(__name__)


class DSNMPS(models.Model):
    _name = "dsn.mps"
    _description = 'MPS'
    _order = 'name desc'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    demand_line_id = fields.Many2one('dsn.demand.planning.line', tracking=True)
    demand_id = fields.Many2one('dsn.demand.planning', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', tracking=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', tracking=True)
    production_qty = fields.Float(string='MPS Qty', tracking=True)
    scheduled_date = fields.Date(tracking=True)
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny", related='demand_id.company_id', tracking=True)
    mo_ids = fields.Many2many('mrp.production', string='Manufacturing Orders', compute='_compute_get_mo')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State',
        compute='_compute_get_mo', copy=False, index=True, readonly=True,
        store=True, tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")
    balance = fields.Float(string='Balance', compute='_compute_get_mo', store=True)


    def replace_name(self):
        for this in self:
            this.name = self.env['ir.sequence'].next_by_code('dsn.mps')

    @api.model
    def create(self, vals):
        res = super(DSNMPS, self).create(vals)
        res.replace_name()
        return res

    def generate_multi_mo(self):
        for this in self:
            if this.mo_ids:
                raise ValidationError(_('MPS %s has created a manufacturing order', this.name))
            
            manufacturing = self.env['mrp.production'].sudo().create({
                'company_id': this.company_id.id,
                'dsn_mps_id': this.id,
                'product_id': this.product_id.id,
                'product_qty': this.production_qty,
                'product_uom_id': this.uom_id.id,
                'date_planned_start': this.scheduled_date,
                'origin': this.name,
                'bom_id': this.bom_id.id,
            })
            manufacturing._onchange_product_id()
            manufacturing._compute_move_raw_ids()
            manufacturing._compute_workorder_ids()

    def _compute_get_mo(self):
        for this in self:
            mo_list = []
            state = False
            balance = this.production_qty
            manufacturing = self.env['mrp.production'].sudo().search([('company_id', '=', self.company_id.id), ('dsn_mps_id', '=', this.id)])
            if manufacturing:
                mo_list.append(manufacturing.id)
                if manufacturing.state == 'done':
                    balance -= manufacturing.product_qty 
    
                state = manufacturing.state
                search_back_order = self.env['mrp.production'].sudo().search([('id', '!=', manufacturing.id),('procurement_group_id', '=', manufacturing.procurement_group_id.id)])
                for backorder in  search_back_order:
                    mo_list.append(backorder.id)
                    if backorder.state == 'done':
                        balance -= backorder.product_qty 
                    state = backorder.state

            if balance < 0:
                balance = 0

            this.balance = balance
            this.state = state
            this.mo_ids = mo_list

    def view_mo(self):
        self.ensure_one()
        view_id = self.env.ref('mrp.mrp_production_form_view').id
        view_tree_id = self.env.ref('mrp.mrp_production_tree_view').id
        action_vals = {
            'name': 'Manufacturing Order',
            'domain': [('id', 'in', self.mo_ids.ids)],
            'view_mode': 'tree,form',
            'res_model': 'mrp.production',
            'views': [[view_tree_id, 'list'],[view_id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'duplicate': False, 'delete': False}
        }
        return action_vals

    
class MRPProduction(models.Model):
    _inherit = 'mrp.production'


    dsn_mps_id = fields.Many2one('dsn.mps', string='MPS', copy=False)



    @api.depends('company_id', 'bom_id', 'product_id', 'product_qty', 'product_uom_id', 'location_src_id', 'date_planned_start')
    def _compute_move_raw_ids(self):
        for production in self:
            if production.state != 'draft':
                continue
            list_move_raw = [Command.link(move.id) for move in production.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
            if not production.bom_id and not production._origin.product_id:
                production.move_raw_ids = list_move_raw
            if production.bom_id != production._origin.bom_id:
                production.move_raw_ids = [Command.clear()]
            if production.bom_id and production.product_id and production.product_qty > 0:
                # keep manual entries
                moves_raw_values = production._get_moves_raw_values()
                move_raw_dict = {move.bom_line_id.id: move for move in production.move_raw_ids.filtered(lambda m: m.bom_line_id)}
                for move_raw_values in moves_raw_values:
                    if move_raw_values['bom_line_id'] in move_raw_dict:
                        # update existing entries
                        list_move_raw += [Command.update(move_raw_dict[move_raw_values['bom_line_id']].id, move_raw_values)]
                    else:
                        # add new entries
                        list_move_raw += [Command.create(move_raw_values)]
                production.move_raw_ids = list_move_raw
            else:
                production.move_raw_ids = [Command.delete(move.id) for move in production.move_raw_ids.filtered(lambda m: m.bom_line_id)]

    @api.depends(
        'move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
        'workorder_ids.state', 'product_qty', 'qty_producing')
    def _compute_state(self):
        for production in self:
            if production.dsn_mps_id and production.state == 'draft':
                production.write({'qty_producing' : 0})
                for move in production.move_raw_ids:
                        move.write({'quantity_done' : 0})
        res = super(MRPProduction, self)._compute_state()
        return res
