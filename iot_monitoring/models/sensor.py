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

    @api.model
    def receive_data(self, machine_code, status, counter, timestamp):

        # 🔍 Cari mesin
        machine = self.env['iot.machine'].search([
            ('name', 'ilike', machine_code),
            ('code', '=', machine_code)
        ], limit=1)

        if not machine:
            return {'success': False, 'error': 'Machine not found'}

        # 🔥 Sync WO
        if hasattr(machine, '_sync_workorder'):
            machine._sync_workorder()

        # 🔍 Ambil WO aktif
        wo = machine._get_active_workorder()

        product_name = wo.product_id.name if wo else '-'

        # =========================
        # 🔥 DELTA DARI MACHINE (LEBIH STABIL)
        # =========================
        last_counter = machine.counter or 0
        delta = counter - last_counter

        print(f"[DEBUG] IN={counter} | MACHINE={last_counter} | DELTA={delta}")

        # 🔁 Handle reset PLC
        if delta < 0:
            delta = counter

        # =========================
        # 🔥 SAVE LOG DULU
        # =========================
        self.create({
            'machine_id': machine.id,
            'status': status,
            'counter': counter,
            'timestamp': timestamp,
            'product_name': product_name,
        })

        # =========================
        # 🔥 UPDATE COUNTER (PASTI NAIK)
        # =========================
        if delta > 0:
            machine.write({
                'counter': machine.counter + delta
            })

        return {'success': True}