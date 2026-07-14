from odoo import http
from odoo.http import request

class MesController(http.Controller):
    @http.route("/mes/start/<int:approval_id>/<int:wo_id>/<int:sequence>", auth="user")
    def start(self, approval_id, wo_id, sequence, **kw):
        approval = request.env["mes.scan.approval"].sudo().browse(approval_id)
        wo = request.env["mrp.workorder"].sudo().browse(wo_id)

        if not approval.exists() or not wo.exists():
            return request.redirect(request.httprequest.referrer or "/web")

        if sequence > 1:

            previous = approval.line_ids.filtered(
                lambda l: l.sequence == sequence - 1
            )[:1]

            if previous and previous.state != "done":
                return request.redirect(request.httprequest.referrer or "/web")

        line = approval.line_ids.filtered(
            lambda l: l.sequence == sequence
        )[:1]

        if not line:
            return request.redirect(request.httprequest.referrer)

        line.action_start()

        return request.redirect(request.httprequest.referrer or "/web")

    @http.route("/mes/stop/<int:wo_id>", auth="user")
    def stop(self, wo_id, **kw):

        wo = request.env["mrp.workorder"].sudo().browse(wo_id)

        if wo.exists():

            wo.write({
                "state": "done",
            })

        return request.redirect(request.httprequest.referrer or "/web")    
    
