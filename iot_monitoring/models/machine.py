from odoo import models, fields, api


class IoTMachine(models.Model):
    _name = 'iot.machine'
    _description = 'IoT Machine'

    name = fields.Char(required=True)
    area_id = fields.Many2one('iot.area', string='Area')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')

    sensor_data_ids = fields.One2many('iot.sensor.data', 'machine_id')
    code = fields.Char(string='Machine Code')

    # 🔥 CORE
    current_workorder_id = fields.Many2one('mrp.workorder')
    counter = fields.Integer(default=0)

    # 🔥 UI
    production_status = fields.Char(compute='_compute_production_status')
    current_product = fields.Char(compute='_compute_production_status')

    latest_counter = fields.Integer(compute='_compute_latest_sensor')
    latest_timestamp = fields.Datetime(compute='_compute_latest_sensor')

    # =========================
    # 🔥 AUTO DETECT WO (REALTIME)
    # =========================
    def _get_active_workorder(self):
        self.ensure_one()

        if not self.workcenter_id:
            return False

        wo = self.env['mrp.workorder'].search([
            ('workcenter_id', '=', self.workcenter_id.id),
            ('state', '=', 'progress'),
        ], order='date_start desc', limit=1)

        return wo

    # =========================
    # 🔥 STATUS + PRODUCT
    # =========================
    @api.depends()
    def _compute_production_status(self):
        for machine in self:
            wo = machine._get_active_workorder()

            # 🔥 AUTO SYNC WO
            if wo != machine.current_workorder_id:
                machine.current_workorder_id = wo
                machine.counter = 0  # RESET

            if wo and wo.state == 'progress':
                machine.production_status = 'progress'
                machine.current_product = wo.product_id.name or '-'
            else:
                machine.production_status = 'stop'
                machine.current_product = '-'
        
        print("WO DETECTED:", wo.name if wo else "NONE")

    # =========================
    # 🔥 COUNTER DISPLAY
    # =========================
    @api.depends('sensor_data_ids', 'sensor_data_ids.counter', 'sensor_data_ids.timestamp')
    def _compute_latest_sensor(self):
        for machine in self:
            latest = self.env['iot.sensor.data'].search([
                ('machine_id', '=', machine.id)
            ], limit=1, order='timestamp desc')
            if latest:
                machine.latest_counter = latest.counter
                machine.latest_timestamp = latest.timestamp
            else:
                machine.latest_counter = 0
                machine.latest_timestamp = False

    # =========================
    # 🔥 DIPANGGIL DARI SENSOR
    # =========================
    def update_counter(self, delta):
        for machine in self:
            machine._sync_workorder()

            machine.counter += delta

    # =========================
    # 🔄 SYNC WO MANUAL (dipakai gateway)
    # =========================
    def _sync_workorder(self):
        for machine in self:
            wo = machine._get_active_workorder()

            if wo and wo != machine.current_workorder_id:
                machine.current_workorder_id = wo
                machine.counter = 0
    

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
        if 'name' in vals:
            vals['code'] = vals['name'].replace(" ", "").upper()
        return super().write(vals)

