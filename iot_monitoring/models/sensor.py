from odoo import models, fields, api

class IoTSensorData(models.Model):
    _name = 'iot.sensor.data'
    _description = 'IoT Sensor Data'
    _order = 'timestamp desc'

    machine_id = fields.Many2one('iot.machine', string='Mesin', required=True)
    status = fields.Selection([
        ('progress', 'In Progress'),
        ('stop', 'Stop Line'),
    ], string='Status', required=True)
    counter = fields.Integer(string='Counter (pcs)')
    timestamp = fields.Datetime(string='Timestamp', required=True)
    product_name = fields.Char(string='Product', store=True)

    @api.model
    def receive_data(self, machine_code, status, counter, timestamp):
        machine = self.env['iot.machine'].search([
            ('workcenter_id.name', '=', machine_code)
        ], limit=1)

        if not machine:
            return {'success': False, 'error': 'Machine not found: ' + machine_code}

        # 🔥 Kita ambil work order yang aktif aja gess
        workorder = self.env['mrp.workorder'].search([
            ('workcenter_id', '=', machine.workcenter_id.id),
            ('state', '=', 'progress'),
        ], limit=1)

        product_name = workorder.product_id.name if workorder else '-'

        # =========================
        # 🔥 AUTO SET WO + RESET
        # =========================
        if workorder and machine.current_workorder_id != workorder:
            machine.current_workorder_id = workorder
            machine.counter = 0

        # =========================
        # ✅ (gob)Log sensor data
        # =========================
        self.create({
            'machine_id': machine.id,
            'status': status,
            'counter': counter,
            'timestamp': fields.Datetime.now(),  # 🔥 pakai ini
            'product_name': product_name,
        })

        # =========================
        # 🔥 Counter
        # =========================
        if workorder:
            machine.counter += counter

        return {'success': True}