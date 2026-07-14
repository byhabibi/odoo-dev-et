from odoo import api, fields, models, _
import re

class SequenceMixin(models.AbstractModel):

    _inherit = 'sequence.mixin'

    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if sequence and date and date > constraint_date:
                format_values = record._get_sequence_format_param(sequence)[1]
                if (
                    format_values['year'] and format_values['year'] != date.year % 10**len(str(format_values['year']))
                    or format_values['month'] and format_values['month'] != date.month
                ):
                    # raise ValidationError(_(
                    #     "The %(date_field)s (%(date)s) doesn't match the %(sequence_field)s (%(sequence)s).\n"
                    #     "You might want to clear the field %(sequence_field)s before proceeding with the change of the date.",
                    #     date=format_date(self.env, date),
                    #     sequence=sequence,
                    #     date_field=record._fields[record._sequence_date_field]._description_string(self.env),
                    #     sequence_field=record._fields[record._sequence_field]._description_string(self.env),
                    # ))
                    pass

    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        for record in self:
            sequence = record[record._sequence_field] or ''
            regex = re.sub(r"\?P<\w+>", "?:", record._sequence_fixed_regex.replace(r"?P<seq>", ""))  # make the seq the only matching group
            matching = re.match(regex, sequence)
            try :
                record.sequence_prefix = sequence[:matching.start(1)]
            except :
                record.sequence_prefix = ''
            record.sequence_number = int(matching.group(1) or 0)