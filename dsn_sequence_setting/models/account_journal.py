from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = "account.journal"

#     sequence_id = fields.Many2one('ir.sequence', string='Entry Sequence',
#                                   help="This field contains the information related to the numbering of the"
#                                        " journal entries of this journal.",
#                                   required=True, copy=False)
#     refund_sequence_id = fields.Many2one('ir.sequence', string='Credit Note Entry Sequence',
#                                          help="This field contains the information related to the "
#                                               "numbering of the credit note entries of this journal.",
#                                          copy=False)
    
    