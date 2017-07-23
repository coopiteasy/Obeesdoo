# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError

class Subscribe(models.TransientModel):
    _name = 'beesdoo.shift.subscribe'

    def _get_date(self):
        date = self.env['res.partner'].browse(self._context.get('active_id')).info_session_date
        if not date:
            return fields.Date.today()
        else:
            return date

    def _get_super(self):
        return self.env['res.partner'].browse(self._context.get('active_id')).super

    def _get_mode(self):
        return self.env['res.partner'].browse(self._context.get('active_id')).working_mode

    cooperator_id = fields.Many2one('res.partner', default=lambda self: self.env['res.partner'].browse(self._context.get('active_id')), required=True)
    info_session = fields.Boolean(string="Followed an information session", default=True)
    info_session_date = fields.Date(string="Date of information session", default=_get_date)
    super = fields.Boolean(string="Super Cooperator", default=_get_super)
    working_mode = fields.Selection(
        [
            ('regular', 'Regular worker'),
            ('irregular', 'Irregular worker'),
            ('exempt', 'Exempted'),
        ], default=_get_mode
    )
    exempt_reason_id = fields.Many2one('cooperative.exempt.reason', 'Exempt Reason')
    shift_id = fields.Many2one('beesdoo.shift.template')
    reset_counter = fields.Boolean(default=False)

    @api.multi
    def subscribe(self):
        if not self.env.user.has_group('beesdoo_shift.group_shift_management'):
            raise UserError(_("You don't have the required access for this operation."))
        if self.cooperator_id == self.env.user.partner_id and not self.env.user.has_group('beesdoo_shift.group_cooperative_admin'):
            raise UserError(_("You cannot subscribe yourself."))
        self.ensure_one()
        self = self.with_context(real_uid=self._uid)
        if self.shift_id and self.shift_id.remaining_worker <= 0:
            raise UserError(_('There is no remaining space for this shift'))
        if self.shift_id:
            #Remove existing shift then subscribe to the new shift
            self.cooperator_id.sudo().write({'subscribed_shift_ids' : [(6,0, [self.shift_id.id])]})
        if self.working_mode != 'regular':
            #Remove existing shift then subscribe to the new shift
            self.cooperator_id.sudo().write({'subscribed_shift_ids' : [(5,)]})

        data = {
            'info_session' : self.info_session,
            'info_session_date': self.info_session_date,
            'working_mode' : self.working_mode,
            'exempt_reason_id' : self.exempt_reason_id.id,
            'super' : self.super,
            'cooperator_id': self.cooperator_id.id,
            'extension_start_time': False,
            'alert_start_time': False,
            'time_extension': 0,
        }
        if self.reset_counter:
            data['sr'] = 0

        status_id = self.env['cooperative.status'].search([('cooperator_id', '=', self.cooperator_id.id)])
        if status_id:
            status_id.sudo().write(data)
        else:
            self.env['cooperative.status'].sudo().create(data)