from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import mimetypes
import base64
import itertools
import logging
_logger = logging.getLogger(__name__)


class DSNMPSWizard(models.TransientModel):
    _name = 'dsn.mps.wizard'
    _inherit = 'base_import.import'
    _description = 'DSN MPS Wizard'


    def _get_default_demand_line(self):
        context = self._context
        model = context.get('active_model')
        return self.env[model].browse(context.get('active_ids')).id

    demand_line_id = fields.Many2one('dsn.demand.planning.line', string='Demand Order Detail', default=_get_default_demand_line)


    def import_mps(self):
        self.ensure_one()
        if not self.file:
            raise ValidationError(_('Please upload your file'))
        content_type = mimetypes.guess_type(self.file_name)
        self.file = base64.decodebytes(self.file)
        self.file_type = content_type[0]

        options = {
            'headers': True, 'advanced': True, 'keep_matches': False, 'encoding': 'utf-8', 'separator': ',', 'quoting': '"', 
            'date_format': '', 'datetime_format': '', 'float_thousand_separator': ',', 'float_decimal_separator': '.', 
            'fields': [], 'use_queue': False
        }
        format_header = ['MPS Qty', 'Scheduled Date']
        file_header = list(itertools.islice(self._read_file(options), 0, None))[1][1]
        if format_header != file_header:
            raise ValidationError(_("Error MPS Import: Invalid file template"))
        
        datas = itertools.islice(self._read_file(options), 1, None)
        for data in datas:
            index_of_interest = None
            for i, sublist in enumerate(data):
                if sublist == ['MPS Qty', 'Scheduled Date']:
                    index_of_interest = i
                    break

            # Extract data after ['MPS Qty', 'Scheduled Date']
            desired_data = data[index_of_interest + 1:]
            no = 0
            for line in desired_data:
                if no == 0:
                    scheduled_date = datetime.strptime(line[1], "%d/%m/%Y").date()
                else:
                    date_object = datetime.strptime(line[1], "%Y-%m-%d")
                    scheduled_date = date_object.strftime("%d/%m/%Y")
                    scheduled_date = datetime.strptime(scheduled_date, "%d/%m/%Y").date()

                if scheduled_date > self.demand_line_id.deadline_date:
                    raise ValidationError(_('Schedule date %s cannot be greater than to deadline date %s', scheduled_date, self.demand_line_id.deadline_date))  
                value = {
                    'product_id': self.demand_line_id.product_id.id,
                    'demand_line_id': self.demand_line_id.id,
                    'demand_id': self.demand_line_id.demand_id.id,
                    'bom_id': self.demand_line_id.bom_id.id,
                    'uom_id': self.demand_line_id.product_id.uom_id.id,
                    'production_qty': line[0],
                    'scheduled_date': scheduled_date
                }
                self.env['dsn.mps'].create(value)
                self.demand_line_id._constrains_mps_qty()

                no += 1

        view_tree = self.env.ref('mrp_forecast_order.dsn_view_mps_tree').id
        action = {
            'name': 'MPS',
            'domain': [('id', 'in', self.demand_line_id.mps_ids.ids)],
            'view_mode': 'tree',
            'res_model': 'dsn.mps',
            'views': [(view_tree, 'tree')],
            'type': 'ir.actions.act_window',
            'context': {'edit': 0, 'create':0, 'copy':0, 'delete':0}
        }

        return action



    def template_import_mps(self):
        return self.env.ref('mrp_forecast_order.action_template_mps_report_xlsx').report_action(self)
