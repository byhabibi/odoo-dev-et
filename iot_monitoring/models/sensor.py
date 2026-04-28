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
        
        machine_code_clean = (machine_code or "").strip()
        
        # Search pakai ilike biar case-insensitive
        machine = self.env['iot.machine'].search([
            ('name', 'ilike', machine_code_clean)
        ], limit=1)

        if not machine:
            return {'success': False, 'error': f'Machine not found: {machine_code_clean}'}

        # Ambil product dari workorder aktif
        product_name = '-'
        if machine.workcenter_id:
            workorder = self.env['mrp.workorder'].search([
                ('workcenter_id', '=', machine.workcenter_id.id),
                ('state', '=', 'progress'),
            ], limit=1)
            if workorder:
                product_name = workorder.product_id.name or '-'

        self.create({
            'machine_id': machine.id,
            'status': status,
            'counter': counter,
            'timestamp': timestamp,
            'product_name': product_name,
        })

        return {'success': True}