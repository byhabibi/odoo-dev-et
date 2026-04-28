from odoo import models, fields, api


class IoTMachine(models.Model):
    _name = 'iot.machine'
    _description = 'IoT Machine'

    name = fields.Char(required=True)
    area_id = fields.Many2one('iot.area', string='Area')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')

    sensor_data_ids = fields.One2many('iot.sensor.data', 'machine_id')

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

        mo = self.env['mrp.workorder'].search([
            ('workcenter_id', '=', self.workcenter_id.id),
            ('state', '=', 'progress'),
        ], order='id desc', limit=1)

        """
        mo = self.env['mrp.production'].search([
            ('state', '=', 'progress'),
            ('product_id', '!=', False),
        ], order='date_start desc', limit=1)
        if not mo:
            return False
        """
        
        if wo:
            return False
        
        wo = self.env['mrp.workorder'].search([
            ('production_id', '=', mo.id),
            ('workcenter_id', '=', self.workcenter_id.id),
        ], order='id desc', limit=1)

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
    @api.depends('counter')
    def _compute_latest_sensor(self):
        for machine in self:
            machine.latest_counter = machine.counter

            latest = self.env['iot.sensor.data'].search([
                ('machine_id', '=', machine.id)
            ], order='timestamp desc', limit=1)

            machine.latest_timestamp = latest.timestamp if latest else False

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

            if wo != machine.current_workorder_id:
                machine.current_workorder_id = wo
                machine.counter = 0


