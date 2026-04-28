from odoo import models, fields, api


class IoTSensorData(models.Model):
    _name = 'iot.sensor.data'
    _description = 'IoT Sensor Data'
    _order = 'timestamp desc'

    machine_id = fields.Many2one('iot.machine', required=True)
    status = fields.Selection([
        ('progress', 'In Progress'),
        ('stop', 'Stop Line'),
    ], required=True)

    counter = fields.Integer()
    timestamp = fields.Datetime(required=True)
    product_name = fields.Char()

    # =========================
    # 🔥 CORE RECEIVE DATA
    # =========================
    @api.model
    def receive_data(self, machine_code, status, counter, timestamp):

        machine = self.env['iot.machine'].search([
            ('workcenter_id.name', '=', machine_code)
        ], limit=1)

        if not machine:
            return {'success': False, 'error': 'Machine not found'}

        # =========================
        # 🔥 GET CURRENT WO
        # =========================
        wo = machine._get_active_workorder()

        product_name = '-'
        if wo:
            product_name = wo.product_id.name or '-'

        # =========================
        # 🔥 HITUNG DELTA (ANTI NUMPUK)
        # =========================
        last_data = self.search([
            ('machine_id', '=', machine.id)
        ], order='timestamp desc', limit=1)

        last_counter = last_data.counter if last_data else 0

        delta = counter - last_counter

        # 🔥 HANDLE RESET PLC
        if delta < 0:
            delta = counter

        # =========================
        # 🔥 UPDATE MACHINE COUNTER
        # =========================
        machine._sync_workorder()
        if delta > 0:
            machine.update_counter(delta)

        # =========================
        # 🔥 SAVE LOG (RAW DATA)
        # =========================
        self.create({
            'machine_id': machine.id,
            'status': status,
            'counter': counter,
            'timestamp': timestamp,
            'product_name': product_name,
        })

        return {'success': True}