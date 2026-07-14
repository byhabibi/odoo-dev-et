from odoo import models, fields, api
import logging
from datetime import timedelta
from collections import Counter
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def name_get(self):
        _logger.warning("=== GET WORKORDER ===")

        result = []

        for rec in self:

            mo = rec.production_id.name or "-"
            wo = rec.name or "-"
            product = rec.production_id.product_id.display_name or "-"
            wc = rec.workcenter_id.name or "-"

            name = f"{mo} | {wo} | {product} | {wc}"

            result.append((rec.id, name))

        return result

class BarcodeScanLog(models.Model):
    _name = "barcode.scan.log"
    _description = "Barcode Scan Log"
    _order = "scan_datetime desc"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True
    )

    barcode = fields.Char(
        related="employee_id.barcode",
        store=True
    )

    scan_datetime = fields.Datetime(
        required=True
    )


class MesScanApproval(models.Model):
    _name = "mes.scan.approval"
    _description = "MES Scan Approval"
    _order = "scan_time desc"

    # =========================
    # OPERATOR
    # =========================

    employee_id = fields.Many2one(
        "hr.employee",
        required=True
    )

    barcode = fields.Char(
        related="employee_id.barcode",
        store=True
    )

    shift_id = fields.Many2one(
        "eran.master.shift",
        string="Shift"
    )

    workcenter_id = fields.Many2one(
        "mrp.workcenter",
        string="Work Center"
    )

    # =========================
    # SCAN
    # =========================

    check_in = fields.Datetime()

    scan_time = fields.Datetime()

    # =========================
    # MES
    # =========================

    line_ids = fields.One2many(
        "mes.scan.approval.line",
        "approval_id",
        string="Work Orders"
    )

    # =========================
    # PRODUKSI
    # =========================

    qty_target = fields.Float()

    qty_actual = fields.Float(default=0)

    sph = fields.Integer()


    # ========================
    # WORK ORDER
    # ========================

    workorder_info = fields.Html(
        string="Today's Assignment",
        compute="_compute_workorder_info",
        sanitize=False,
    )

    def _render_downtime_html(self, line):
        if not line.downtime_ids:
            return ""

        reason_label = {
            "material": "Material Habis",
            "machine": "Problem Mesin",
        }

        items = ""
        for d in line.downtime_ids.sorted("start_time", reverse=True):
            start_str = self._format_downtime_time(d.start_time)
            end_str = self._format_downtime_time(d.end_time)
            note_str = f"<br/><i>Catatan: {d.note}</i>" if d.note else ""

            items += f"""
            <li style="margin-bottom:6px;">
                <b>{reason_label.get(d.reason, d.reason)}</b> —
                dari {start_str} sampai {end_str}
                {note_str}
            </li>
            """

        return f"""
        <div style="margin-top:8px;">
            <b>Riwayat Downtime</b>
            <ul style="padding-left:18px;margin:4px 0 0 0;">
                {items}
            </ul>
        </div>
        """

    def _render_productivity_period_html(self, line):
        start_time, end_time = self._get_productivity_period(line)

        if not start_time:
            return ""

        start_str = self._format_downtime_time(start_time)
        end_str = self._format_downtime_time(end_time)

        return f"""
        <div style="margin-top:8px;">
            <b>Productivity Period</b>

            <div style="margin:4px 0 0 0;">
                {start_str} sampai {end_str}
            </div>  
        </div>
        """

    def _get_productivity_period(self, line):
        productivity_lines = line.workorder_id.time_ids.filtered(lambda t: t.date_start)

        if productivity_lines:
            start_time = min(productivity_lines.mapped("date_start"))
            closed_times = productivity_lines.filtered(lambda t: t.date_end)
            has_open_time = bool(productivity_lines.filtered(lambda t: not t.date_end))

            if line.state == "running" or has_open_time:
                return start_time, False

            if closed_times:
                return start_time, max(closed_times.mapped("date_end"))

            return start_time, False

        return line.start_time, line.stop_time

    def _format_downtime_time(self, value):
        if not value:
            return "-"

        tz_record = self.with_context(tz=self.env.user.tz or "Asia/Jakarta")
        local_time = fields.Datetime.context_timestamp(tz_record, value)
        return local_time.strftime("%d/%m/%Y %H:%M")
    
    @api.depends(
        "check_in",
        "employee_id",
        "line_ids",
        "line_ids.state",
        "line_ids.start_time",
        "line_ids.stop_time",
        "line_ids.workorder_id.time_ids.date_start",
        "line_ids.workorder_id.time_ids.date_end",
        "line_ids.downtime_ids",
        "line_ids.downtime_ids.reason",
        "line_ids.downtime_ids.note",
        "line_ids.downtime_ids.start_time",
        "line_ids.downtime_ids.end_time",
    )
    def _compute_workorder_info(self):

        for rec in self:

            if not rec.check_in:
                rec.workorder_info = ""
                continue

            lines = rec.line_ids.sorted("sequence")

            if not lines:
                rec.workorder_info = "<p style='color:#999;'>Tidak ada Work Order untuk hari ini.</p>"
                continue

            active_lines = lines.filtered(lambda l: l.state != "done")
            done_lines = lines.filtered(lambda l: l.state == "done")

            html = []

            # ===================================
            # SECTION AKTIF (nomor urut sendiri)
            # ===================================
            total_active = len(active_lines)

            for idx, line in enumerate(active_lines, start=1):

                wo = line.workorder_id
                leader = wo.leader_id.name if wo.leader_id else "-"

                if line.state != "running" and not line.can_start:
                    html.append(f"""
                    <div style="
                        border:1px solid #dcdcdc;
                        border-radius:8px;
                        padding:12px;
                        margin-bottom:12px;
                        background:#f8f9fa;
                    ">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
                            <h4 style="margin:0;color:#0b72b9;">
                                {wo.workcenter_id.name} ({idx}/{total_active})
                            </h4>
                            <div style="text-align:right;white-space:nowrap;">
                                <span style="
                                    display:inline-block;
                                    padding:3px 10px;
                                    border-radius:12px;
                                    background:#e9ecef;
                                    color:#555;
                                    font-size:12px;
                                    font-weight:bold;
                                    margin-right:8px;
                                ">{line.state.upper()}</span>
                            </div>
                        </div>
                    </div>
                    """)
                    continue

                button = ""

                if line.can_start and line.state in ("ready", "waiting"):
                    button = f"""
                        <a href="/mes/start/{line.id}"
                            style="display:inline-block;padding:8px 18px;background:#28a745;
                            color:white;border-radius:5px;text-decoration:none;font-weight:bold;">
                            START
                        </a>
                    """
                elif line.state == "running":
                    button = f"""
                        <a href="/mes/stop/{line.id}"
                            style="display:inline-block;padding:8px 18px;background:#dc3545;
                            color:white;border-radius:5px;text-decoration:none;font-weight:bold;">
                            STOP
                        </a>
                    """

                html.append(f"""
                <div style="
                    border:1px solid #dcdcdc;
                    border-radius:8px;
                    padding:12px;
                    margin-bottom:12px;
                    background:#fafafa;
                ">
                    <h4 style="margin:0;color:#0b72b9;">
                        📍 {wo.workcenter_id.name} ({idx}/{total_active})
                    </h4>

                    <p><b>Leader :</b> {leader}</p>
                    <p><b>Manufacturing Order</b><br/>{wo.production_id.name}</p>
                    <p><b>Work Order</b><br/>{wo.name}</p>
                    <p><b>Product</b><br/>{wo.product_id.display_name}</p>
                    <p><b>Target</b><br/>{line.qty_target}</p>
                    <p><b>Status</b><br/>{line.state.upper()}</p> 
                    {rec._render_downtime_html(line)}
                    {rec._render_productivity_period_html(line)}

                    <div style="text-align:right; margin-top:15px;">
                        {button}
                    </div>
                </div>
                """)

            if not active_lines:
                html.append("<p style='color:#28a745;font-weight:bold;'>🎉 Semua Work Order hari ini sudah selesai.</p>")

            # ===================================
            # SECTION SUDAH SELESAI (nomor urut sendiri, terpisah di bawah)
            # ===================================
            if done_lines:

                total_done = len(done_lines)

                html.append("""
                <hr style="margin:24px 0;border:none;border-top:2px dashed #ccc;" />
                <h3 style="color:#555;margin-bottom:12px;">Sudah Selesai</h3>
                """)

                for idx, line in enumerate(done_lines, start=1):

                    wo = line.workorder_id
                    leader = wo.leader_id.name if wo.leader_id else "-"

                    html.append(f"""
                    <div style="
                        border:1px solid #28a745;
                        border-radius:8px;
                        padding:12px;
                        margin-bottom:12px;
                        background:#f4fbf6;
                    ">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <h4 style="margin:0;color:#0b72b9;">
                                📍 {wo.workcenter_id.name} ({idx}/{total_done})
                            </h4>
                            <span style="
                                background:#28a745;color:white;padding:2px 10px;
                                border-radius:12px;font-size:12px;font-weight:bold;
                            ">✅ SELESAI</span>
                        </div>

                        <p><b>Leader :</b> {leader}</p>
                        <p><b>Manufacturing Order</b><br/>{wo.production_id.name}</p>
                        <p><b>Work Order</b><br/>{wo.name}</p>
                        <p><b>Product</b><br/>{wo.product_id.display_name}</p>
                        <p><b>Target</b><br/>{line.qty_target}</p>
                        <p><b>Status</b><br/>{line.state.upper()}</p>
                        {rec._render_downtime_html(line)}
                        {rec._render_productivity_period_html(line)}
                    </div>
                    """)

            rec.workorder_info = "".join(html)

    # =========================
    # STATUS
    # =========================

    state = fields.Selection([
        ("draft", "Waiting"),
        ("ready", "Ready"),
        ("running", "Running"),
        ("done", "Done"),
    ], default="draft")

    start_time = fields.Datetime()

    stop_time = fields.Datetime()

    duration = fields.Float()

    note = fields.Text()

    def action_approve(self):
        self.write({
            "state": "ready"
        })
        return True

    def action_reject(self):
        self.write({
            "state": "draft"
        })
        return True
    
    def action_start_workorder(self, workorder, sequence):
        self.ensure_one()
        _logger.warning("========== START ==========")

        workorder.write({
            "operator_id": self.employee_id.id,
            "shift_id": self.shift_id.id,
            "start_time": fields.Datetime.now(),
            "state": "progress",
        })

        self.write({
            "state": "running"
        })

        return True
    
    def action_stop_workorder(self):
        self.ensure_one()

        _logger.warning("========== STOP ==========")

        self.write({
            "state": "ready",
        })

        return True

class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    shift_id = fields.Many2one("eran.master.shift", string="Shift")
    # scan_time sudah di-handle oleh Odoo lewat field 'date_start'

class MesScanApprovalLine(models.Model):
    _name = "mes.scan.approval.line"
    _description = "MES Scan Approval Line"

    approval_id = fields.Many2one(
        "mes.scan.approval",
        required=True,
        ondelete="cascade",
    )

    sequence = fields.Integer()

    workorder_id = fields.Many2one(
        "mrp.workorder",
        required=True,
    )

    production_id = fields.Many2one(
        related="workorder_id.production_id",
        store=True,
    )

    workcenter_id = fields.Many2one(
        related="workorder_id.workcenter_id",
        store=True,
    )

    leader_id = fields.Many2one(
        related="workorder_id.leader_id",
        store=True,
    )

    product_id = fields.Many2one(
        related="workorder_id.product_id",
        store=True,
    )

    # ===== TARGET PRODUKSI =====

    qty_target = fields.Float(
        related="workorder_id.production_id.product_qty",
        store=True,
    )

    qty_actual = fields.Float(default=0)

    sph = fields.Integer()

    # ===== STATUS =====

    state = fields.Selection([
        ("ready", "Ready"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("done", "Done"),
    ], default="ready")

    start_time = fields.Datetime()

    stop_time = fields.Datetime()

    duration = fields.Float()

    stop_reason = fields.Selection([
        ("material", "Material Habis"),
        ("machine", "Problem Mesin"),
        ("done", "Pekerjaan Telah Selesai"),
    ], string="Alasan Stop")

    can_start = fields.Boolean(compute="_compute_can_start")

    @api.depends("sequence", "approval_id.line_ids.state", "approval_id.line_ids.sequence")
    def _compute_can_start(self):
        for line in self:
            prior_lines = line.approval_id.line_ids.filtered(
                lambda l: l.sequence < line.sequence
            )
            line.can_start = all(l.state == "done" for l in prior_lines)

    def action_start(self):
        self.ensure_one()

        if not self.can_start:
            raise UserError("Selesaikan terlebih dahulu Work Order yang sedang berjalan.")

        wo = self.workorder_id.sudo()

        if self.state == "done":
            raise UserError("Work Order ini sudah selesai dan tidak bisa di-start lagi.")

        if wo.state == "cancel":
            raise UserError("Work Order ini sudah dibatalkan.")

        scan_time = fields.Datetime.now()

        if wo.date_planned_finished and wo.date_planned_finished < scan_time:
            wo.date_planned_finished = scan_time + timedelta(hours=1)

        if wo.date_planned_start and wo.date_planned_start > wo.date_planned_finished:
            wo.date_planned_start = scan_time

        if wo.state != "progress":
            wo.button_start()
        else:
            open_time = wo.time_ids.filtered(lambda t: not t.date_end)
            if not open_time:
                wo.button_start()

        open_time = wo.time_ids.filtered(lambda t: not t.date_end)
        if open_time:
            open_time[0].write({"date_start": scan_time})

        # ===== TUTUP DOWNTIME YANG MASIH TERBUKA =====
        open_downtime = self.downtime_ids.filtered(lambda d: not d.end_time)
        if open_downtime:
            open_downtime[0].write({"end_time": scan_time})

        self.write({
            "state": "running",
            "start_time": scan_time,
        })

        if self.approval_id.state != "running":
            self.approval_id.write({"state": "running"})

    def action_stop(self, reason, note=None):
        self.ensure_one()

        wo = self.workorder_id.sudo()
        now = fields.Datetime.now()

        duration = 0.0
        if self.start_time:
            duration = (now - self.start_time).total_seconds() / 60.0

        if reason == "done":
            self._stop_workorder_without_validating_production(wo, now)

            vals = {
                "stop_time": now,
                "duration": self.duration + duration,
                "stop_reason": reason,
                "state": "done",
            }

        else:
            open_time = wo.time_ids.filtered(lambda t: not t.date_end)
            if open_time:
                open_time[0].write({"date_end": now})

            # ===== BIKIN RECORD DOWNTIME BARU =====
            self.env["mes.scan.approval.line.downtime"].sudo().create({
                "line_id": self.id,
                "reason": reason,
                "note": note,
                "start_time": now,
            })

            vals = {
                "stop_time": now,
                "duration": self.duration + duration,
                "stop_reason": reason,
                "state": "ready",
            }

        self.write(vals)

    def _stop_workorder_without_validating_production(self, workorder, stop_time):
        workorder = workorder.sudo()

        open_time = workorder.time_ids.filtered(lambda t: not t.date_end)
        if open_time:
            open_time[0].write({"date_end": stop_time})

        if workorder.state not in ("done", "cancel"):
            workorder.end_all()
            workorder.with_context(bypass_duration_calculation=True).write({
                "qty_produced": workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                "state": "done",
                "date_finished": stop_time,
                "date_planned_finished": stop_time,
                "costs_hour": workorder.workcenter_id.costs_hour,
            })
        else:
            workorder.write({
                "date_planned_finished": stop_time,
            })

        if workorder.production_id:
            workorder.production_id.write({
                "end_time": stop_time,
            })

    downtime_ids = fields.One2many(
        "mes.scan.approval.line.downtime",
        "line_id",
        string="Riwayat Downtime",
    )

class MesScanApprovalLineDowntime(models.Model):
    _name = "mes.scan.approval.line.downtime"
    _description = "MES Downtime Log"
    _order = "start_time desc"

    line_id = fields.Many2one(
        "mes.scan.approval.line",
        required=True,
        ondelete="cascade",
    )

    reason = fields.Selection([
        ("material", "Material Habis"),
        ("machine", "Problem Mesin"),
    ], required=True)

    note = fields.Text()

    start_time = fields.Datetime(required=True)  
    end_time = fields.Datetime()                  
