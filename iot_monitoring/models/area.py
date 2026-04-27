from odoo import models, fields, api

class IoTArea(models.Model):
    _name = 'iot.area'
    _description = 'IoT Area'

    name = fields.Char(required=True)
    machine_ids = fields.One2many('iot.machine', 'area_id', string='Machines')
    machine_count = fields.Integer(
        string='Jumlah Mesin',
        compute='_compute_machine_count',
        store=True
    )

    @api.depends('machine_ids')
    def _compute_machine_count(self):
        for area in self:
            area.machine_count = len(area.machine_ids)