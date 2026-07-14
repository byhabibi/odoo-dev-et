import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MesScanController(http.Controller):

    def _info_page(self, title, message, color="#28a745"):
        html = f"""
        <html>
        <head><meta charset="utf-8"/><title>{title}</title></head>
        <body style="
            font-family: -apple-system, Arial, sans-serif;
            background:#f4f4f4;
            display:flex;
            align-items:center;
            justify-content:center;
            height:100vh;
            margin:0;
        ">
            <div style="
                background:white;
                border-radius:12px;
                padding:30px;
                box-shadow:0 4px 20px rgba(0,0,0,0.15);
                width:320px;
                text-align:center;
            ">
                <div style="font-size:40px;margin-bottom:10px;">
                    {"✅" if color == "#28a745" else "⚠️"}
                </div>
                <h3 style="margin:0 0 8px 0;color:{color};">{title}</h3>
                <p style="color:#555;font-size:14px;">{message}</p>
                <p style="color:#999;font-size:12px;margin-top:20px;">
                    Silakan kembali ke tab sebelumnya.
                </p>
            </div>
        </body>
        </html>
        """
        return request.make_response(html)

    # ===================================
    # START
    # ===================================

    @http.route("/mes/start/<int:line_id>", type="http", auth="user")
    def mes_start(self, line_id, **kwargs):
        line = request.env["mes.scan.approval.line"].sudo().browse(line_id)

        if not line.exists():
            return self._info_page("Gagal", f"Line ID {line_id} tidak ditemukan.", color="#dc3545")

        try:
            line.action_start()
        except UserError as e:
            return self._info_page("Belum Bisa Dimulai", str(e), color="#dc3545")
        except Exception as e:
            _logger.exception("ERROR saat action_start line_id=%s", line_id)
            return self._info_page("Terjadi Kesalahan", str(e), color="#dc3545")

        wo = line.workorder_id
        return self._info_page(
            "MO Sudah Berjalan",
            f"{wo.name} — {wo.production_id.name} sudah dimulai.",
        )

    # ===================================
    # STOP — pilihan alasan
    # ===================================

    @http.route("/mes/stop/<int:line_id>", type="http", auth="user")
    def mes_stop(self, line_id, **kwargs):
        line = request.env["mes.scan.approval.line"].sudo().browse(line_id)

        if not line.exists():
            return self._info_page("Gagal", f"Line ID {line_id} tidak ditemukan.", color="#dc3545")

        html = f"""
        <html>
        <head><meta charset="utf-8"/><title>Pilih Alasan Stop</title></head>
        <body style="
            font-family: -apple-system, Arial, sans-serif;
            background:#f4f4f4;
            display:flex;
            align-items:center;
            justify-content:center;
            height:100vh;
            margin:0;
        ">
            <div style="
                background:white;
                border-radius:12px;
                padding:30px;
                box-shadow:0 4px 20px rgba(0,0,0,0.15);
                width:320px;
                text-align:center;
            ">
                <h3 style="margin-top:0;">Kenapa dihentikan?</h3>
                <p style="color:#777;font-size:13px;">
                    {line.workorder_id.name} — {line.workorder_id.production_id.name}
                </p>

                <a href="/mes/stop/{line.id}/confirm?reason=material"
                    style="display:block;margin:10px 0;padding:12px;
                    background:#ffc107;color:#000;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
                    Material Habis
                </a>

                <a href="/mes/stop/{line.id}/note?reason=machine"
                    style="display:block;margin:10px 0;padding:12px;
                    background:#dc3545;color:white;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
                    Problem Mesin
                </a>

                <a href="/mes/stop/{line.id}/confirm?reason=done"
                    style="display:block;margin:10px 0;padding:12px;
                    background:#28a745;color:white;border-radius:6px;
                    text-decoration:none;font-weight:bold;">
                    Pekerjaan Telah Selesai
                </a>
            </div>
        </body>
        </html>
        """

        return request.make_response(html)

    # ===================================
    # NOTE FORM — khusus Problem Mesin
    # ===================================

    @http.route("/mes/stop/<int:line_id>/note", type="http", auth="user")
    def mes_stop_note(self, line_id, reason=None, **kwargs):
        line = request.env["mes.scan.approval.line"].sudo().browse(line_id)

        if not line.exists():
            return self._info_page("Gagal", f"Line ID {line_id} tidak ditemukan.", color="#dc3545")

        if reason != "machine":
            return self._info_page("Gagal", "Alasan tidak valid.", color="#dc3545")

        reason_label = {
            "machine": "Problem Mesin",
        }[reason]

        html = f"""
        <html>
        <head><meta charset="utf-8"/><title>Catatan</title></head>
        <body style="
            font-family: -apple-system, Arial, sans-serif;
            background:#f4f4f4;
            display:flex;
            align-items:center;
            justify-content:center;
            height:100vh;
            margin:0;
        ">
            <div style="
                background:white;
                border-radius:12px;
                padding:30px;
                box-shadow:0 4px 20px rgba(0,0,0,0.15);
                width:340px;
                text-align:center;
            ">
                <h3 style="margin-top:0;">{reason_label}</h3>
                <p style="color:#777;font-size:13px;">
                    {line.workorder_id.name} — {line.workorder_id.production_id.name}
                </p>

                <form action="/mes/stop/{line.id}/confirm" method="get">
                    <input type="hidden" name="reason" value="{reason}"/>
                    <textarea name="note" rows="4" placeholder="Catatan (opsional)..."
                        style="width:100%;padding:10px;border-radius:6px;
                        border:1px solid #ccc;font-family:inherit;
                        box-sizing:border-box;resize:vertical;"></textarea>

                    <button type="submit"
                        style="display:block;width:100%;margin-top:14px;padding:12px;
                        background:#0b72b9;color:white;border:none;border-radius:6px;
                        font-weight:bold;font-size:14px;cursor:pointer;">
                        OK
                    </button>
                </form>
            </div>
        </body>
        </html>
        """

        return request.make_response(html)

    # ===================================
    # STOP CONFIRM
    # ===================================

    @http.route("/mes/stop/<int:line_id>/confirm", type="http", auth="user")
    def mes_stop_confirm(self, line_id, reason=None, note=None, **kwargs):
        line = request.env["mes.scan.approval.line"].sudo().browse(line_id)

        if not line.exists():
            return self._info_page("Gagal", f"Line ID {line_id} tidak ditemukan.", color="#dc3545")

        if reason not in ("material", "machine", "done"):
            return self._info_page("Gagal", "Alasan tidak valid.", color="#dc3545")

        try:
            line.action_stop(reason, note=note)
        except Exception as e:
            _logger.exception("ERROR saat action_stop line_id=%s reason=%s", line_id, reason)
            return self._info_page("Terjadi Kesalahan", str(e), color="#dc3545")

        reason_label = {
            "material": "Material Habis",
            "machine": "Problem Mesin",
            "done": "Pekerjaan Telah Selesai",
        }[reason]

        return self._info_page(
            "Work Order Dihentikan",
            f"{line.workorder_id.name} dihentikan — {reason_label}.",
        )

    #==================================
    # Kiosk Mode
    #==================================
    
    # @http.route("/mes/kiosk", type="http", auth="user")
    # def mes_kiosk(self, **kwargs):
    #     html = """
    #     <html>
    #     <head>
    #         <meta charset="utf-8"/>
    #         <title>MES Scan Station</title>
    #     </head>
    #     <body style="
    #         font-family: -apple-system, Arial, sans-serif;
    #         background:#0b72b9;
    #         display:flex;
    #         align-items:center;
    #         justify-content:center;
    #         height:100vh;
    #         margin:0;
    #     ">
    #         <div style="
    #             background:white;
    #             border-radius:16px;
    #             padding:50px;
    #             text-align:center;
    #             width:400px;
    #             box-shadow:0 8px 30px rgba(0,0,0,0.2);
    #         ">
    #             <h2 style="margin-top:0;color:#333;">Scan Badge Kamu</h2>
    #             <p style="color:#888;font-size:14px;">Dekatkan barcode ke scanner</p>

    #             <form id="scanForm" action="/mes/kiosk/scan" method="get">
    #                 <input
    #                     id="barcodeInput"
    #                     name="barcode"
    #                     type="text"
    #                     autocomplete="off"
    #                     style="
    #                         width:100%;
    #                         padding:16px;
    #                         font-size:20px;
    #                         text-align:center;
    #                         border:2px solid #ddd;
    #                         border-radius:8px;
    #                         box-sizing:border-box;
    #                     "
    #                 />
    #             </form>
    #         </div>

    #         <script>
    #             var input = document.getElementById('barcodeInput');
    #             input.focus();

    #             // barcode scanner biasanya ngetik cepat + diakhiri Enter
    #             input.addEventListener('keypress', function(e) {
    #                 if (e.key === 'Enter') {
    #                     document.getElementById('scanForm').submit();
    #                 }
    #             });

    #             // auto-refocus kalau user klik area lain
    #             document.body.addEventListener('click', function() {
    #                 input.focus();
    #             });
    #         </script>
    #     </body>
    #     </html>
    #     """
    #     return request.make_response(html)


    # @http.route("/mes/kiosk/scan", type="http", auth="user")
    # def mes_kiosk_scan(self, barcode=None, **kwargs):
    #     if not barcode:
    #         return request.redirect("/mes/kiosk")

    #     result = request.env["hr.employee"].sudo()._mes_get_or_create_approval(barcode)

    #     if isinstance(result, dict) and "error" in result:
    #         return self._info_page("Tidak Bisa Lanjut", result["error"], color="#dc3545")

    #     if not result:
    #         return self._info_page("Gagal", "Barcode tidak dikenali.", color="#dc3545")

    #     # ===== REDIRECT LANGSUNG KE CARD APPROVAL MILIK DIA =====
    #     return request.redirect(f"/odoo/mes-scan-approval/{result.id}")