
from odoo import _, fields, models, api
from odoo.exceptions import UserError, ValidationError

class DSNForecastOrder(models.Model):
    _name = "dsn.forecast.order"
    _description = 'Forecast Order'
    _order = 'name'
    _inherit = ["mail.thread", "mail.activity.mixin"]


    name = fields.Char(default='New', tracking=True)
    type = fields.Selection([('forecast_order', 'Forecast Order')], tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('done', 'Done')], default='draft', tracking=True)
    forecast_line_ids = fields.One2many('dsn.forecast.order.line', 'forecast_id')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny", default=lambda self: self.env.user.company_id, tracking=True)


    def button_generate_pricelist(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_("Only generate draft records!."))
            
            for line in rec.forecast_line_ids:
                # cari pircelist
                product_company = line.company_id.id
                product_currency = line.product_id.currency_id.id
                product_quantity = line.quantity
                product_forecast_date = line.forecast_date
                

                pricelist = self.env['product.pricelist'].search([
                    ('company_id', '=', product_company), 
                    ('currency_id', '=', product_currency),
                ])

                for price in pricelist.item_ids:
                    if price.min_quantity <= product_quantity and (price.date_start.date() <= product_forecast_date and price.date_end.date() >= product_forecast_date):
                        line.price = price.fixed_price

    def replace_name(self):
        for this in self:
            if this.type == 'forecast_order':
                this.name = self.env['ir.sequence'].next_by_code('forecast.order')

    @api.model
    def create(self, vals):
        res = super(DSNForecastOrder, self).create(vals)
        res.replace_name()
        return res
    
    def button_to_confirm(self):
        if not self.forecast_line_ids:
             raise ValidationError(_("Forecast details cannot be empty."))
        self.write({'state': 'confirm'})

    def reset_to_draft(self):
        self.write({'state': 'draft'})

    def unlink(self):
        for this in self:
            if this.state != 'draft':
                raise ValidationError(_("Cannot delete with status %s.", this.state))
        return super(DSNForecastOrder, self).unlink()


class DSNForecastOrderLine(models.Model):
    _name = "dsn.forecast.order.line"
    _description = 'Forecast Order Line'


    @api.model
    def _get_default_currency(self):
        return self.env.company.currency_id

    forecast_id = fields.Many2one('dsn.forecast.order', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    partner_id = fields.Many2one('res.partner', string='Customer')
    currency_id = fields.Many2one('res.currency', default=_get_default_currency)
    price = fields.Float(default=1.0)
    quantity = fields.Float(default=1.0)
    total = fields.Float(compute='_compute_total', store=True)
    forecast_date = fields.Date()
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, help="Comapny", related='forecast_id.company_id')
    is_demand_order = fields.Boolean(string='Demand Order')


    @api.onchange('product_id')
    def _onchange_product(self):
        self.price = 0
        if self.product_id:
            self.price = self.product_id.list_price
            self.uom_id = self.product_id.uom_id

    @api.depends('price', 'quantity')
    def _compute_total(self):
        for line in self:
            line.total = line.quantity*line.price

    @api.constrains('quantity', 'price')
    def _constrains_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Quantity cannot be minus or 0."))
            if line.price <= 0:
                raise ValidationError(_("Price cannot be minus or 0."))