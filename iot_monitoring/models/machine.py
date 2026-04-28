from odoo import models, fields, api


class IoTMachine(models.Model):
    _name = 'iot.machine'
    _description = 'IoT Machine'

    name = fields.Char(required=True)
    area_id = fields.Many2one('iot.area', string='Area')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')
    sensor_data_ids = fields.One2many('iot.sensor.data', 'machine_id')
    code = fields.Char(string='Machine Code')

    # Core
    current_workorder_id = fields.Many2one('mrp.workorder')
    counter = fields.Integer(default=0, store=True)
    latest_timestamp = fields.Datetime(store=True)

    # UI computed
    production_status = fields.Char(
        compute='_compute_production_status',
        store=False
    )
    current_product = fields.Char(
        compute='_compute_production_status',
        store=False
    )

    # Alias untuk kanban — langsung dari field counter
    latest_counter = fields.Integer(
        compute='_compute_latest_counter',
        store=False
    )

    @api.depends('counter')
    def _compute_latest_counter(self):
        for machine in self:
            machine.latest_counter = machine.counter

    def _get_active_workorder(self):
        self.ensure_one()
        if not self.workcenter_id:
            return False
        return self.env['mrp.workorder'].search([
            ('workcenter_id', '=', self.workcenter_id.id),
            ('state', '=', 'progress'),
        ], order='date_start desc', limit=1)

    @api.depends()
    def _compute_production_status(self):
        for machine in self:
            wo = machine._get_active_workorder()
            if wo and wo.state == 'progress':
                machine.production_status = 'progress'
                machine.current_product = wo.product_id.name or '-'
            else:
                machine.production_status = 'stop'
                machine.current_product = '-'

    def _sync_workorder(self):
        """Dipanggil dari sensor saat data masuk"""
        for machine in self:
            wo = machine._get_active_workorder()
            if wo and wo.id != machine.current_workorder_id.id:
                # WO baru → reset counter
                machine.write({
                    'current_workorder_id': wo.id,
                    'counter': 0,
                    'latest_timestamp': fields.Datetime.now(),
                })

    def action_open_workorders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders - ' + self.name,
            'res_model': 'mrp.workorder',
            'view_mode': 'kanban,list,form',
            'domain': [
                ('workcenter_id', '=', self.workcenter_id.id),
                ('state', 'in', ['ready', 'progress']),
            ],
            'target': 'new',
        }

    def action_open_monitoring(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Monitoring - ' + self.name,
            'res_model': 'iot.production.summary',
            'view_mode': 'graph',
            'domain': [('machine_id', '=', self.id)],
            'context': {'default_machine_id': self.id},
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if not vals.get('code') and vals.get('name'):
            vals['code'] = vals['name'].replace(" ", "").upper()
        return super().create(vals)

    def write(self, vals):
        if 'name' in vals and 'code' not in vals:
            vals['code'] = vals['name'].replace(" ", "").upper()
        return super().write(vals)