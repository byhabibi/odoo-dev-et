from odoo import models, fields, api

class IoTMachine(models.Model):
    _name = 'iot.machine'
    _description = 'IoT Machine'

    name = fields.Char(required=True)
    area_id = fields.Many2one('iot.area', string='Area')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')

    # 🔗 RELASI
    sensor_data_ids = fields.One2many('iot.sensor.data', 'machine_id', string='Sensor Data')

    # 🔥 CORE SYSTEM
    current_workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Current Work Order'
    )

    counter = fields.Integer(
        string='Actual Counter',
        default=0
    )

    # 🎯 UI (Joko UI)
    production_status = fields.Char(
        string='Status',
        compute='_compute_production_status'
    )

    current_product = fields.Char(
        string='Product',
        compute='_compute_production_status'
    )

    latest_counter = fields.Integer(
        string='Counter Terkini',
        compute='_compute_latest_sensor'
    )

    latest_timestamp = fields.Datetime(
        string='Update Terakhir',
        compute='_compute_latest_sensor'
    )

    # =========================
    # 🔥 Status Cok
    # =========================
    @api.depends('current_workorder_id')
    def _compute_production_status(self):
        for machine in self:
            wo = machine.current_workorder_id

            if wo and wo.state == 'progress':
                machine.production_status = 'progress'
                machine.current_product = wo.product_id.name or '-'
            else:
                machine.production_status = 'stop'
                machine.current_product = '-'

    # =========================
    # 🔥 Counter Angzay
    # =========================
    @api.depends('counter')
    def _compute_latest_sensor(self):
        for machine in self:
            machine.latest_counter = machine.counter

            latest = self.env['iot.sensor.data'].search([
                ('machine_id', '=', machine.id)
            ], order='timestamp desc', limit=1)

            machine.latest_timestamp = latest.timestamp if latest else False

    # =========================
    # 🔄 SET WORKORDER + RESET
    # =========================
    def set_workorder(self, workorder):
        for machine in self:
            if machine.current_workorder_id != workorder:
                machine.current_workorder_id = workorder
                machine.counter = 0

    # =========================
    # 🤖 AUTO DETECT WO (Kali bisa wkwk)
    # =========================
    def auto_update_workorder(self):
        for machine in self:
            wo = self.env['mrp.workorder'].search([
                ('workcenter_id', '=', machine.workcenter_id.id),
                ('state', '=', 'progress'),
            ], limit=1)

            if wo != machine.current_workorder_id:
                machine.current_workorder_id = wo
                machine.counter = 0

    # =========================
    # 🔗 ACTION UI
    # =========================
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