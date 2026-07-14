import logging
from odoo import models, fields
_logger = logging.getLogger(__name__)


class PartnerXlsx(models.AbstractModel):
    _name = 'report.mrp_forecast_order.template_import_mps_report_xlsx'
    _description = "Template Import MPS"
    _inherit = 'report.report_xlsx.abstract'


    def generate_xlsx_report(self, workbook, data, objects):
        sheet = workbook.add_worksheet('Template MPS')

        text_title_style = workbook.add_format({'font_name': 'Arial', 'font_size': 6, 'bold': True,'text_wrap': True,
            'align': 'center', 'font_color': '#028096'})
        text_header_style1 = workbook.add_format({'font_name': 'Arial', 'font_size': 6, 'text_wrap': True, 'align': 'center',
            'border':False})
        num_style = workbook.add_format({'num_format': '#,##0.00', 'font_name': 'Arial', 'font_size': 6, 'align': 'center'})
        text_thead_style = workbook.add_format({'font_name': 'Arial', 'font_size': 6, 'text_wrap': True, 'align': 'center',
            'bg_color': '#E1E1E1', 'border':True})
        

        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 10)
        sheet.set_column('D:D', 10)


        product = 'Product : ' + str(objects.demand_line_id.product_id.display_name)
        bom = 'Bill of Material : ' + str(objects.demand_line_id.bom_id.display_name)

        sheet.write_row(0, 0, [product], text_title_style)
        sheet.write_row(0, 1, [bom], text_title_style)

        sheet.write_row(2, 0, ['MPS Qty'], text_thead_style)
        sheet.write_row(2, 1, ['Scheduled Date'], text_thead_style)

        mps_qty = [100]
        schedule_date = [str(fields.date.today().strftime('%d/%m/%Y'))]

        row = 2
        row += 1
        sheet.write_column(row, 0, mps_qty, num_style)
        sheet.write_column(row, 1, schedule_date, text_header_style1)