odoo.define('eran_custom.mes_kiosk_mode', function (require) {
"use strict";

var KioskMode = require('hr_attendance.kiosk_mode');
var core = require('web.core');

var MesKioskMode = KioskMode.extend({

    _onBarcodeScanned: function (barcode) {
        var self = this;
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._rpc({
                model: 'hr.employee',
                method: 'mes_kiosk_scan',
                args: [barcode],
            })
            .then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.displayNotification({ title: result.warning, type: 'danger' });
                    core.bus.on('barcode_scanned', self, self._onBarcodeScanned);
                }
            }, function () {
                core.bus.on('barcode_scanned', self, self._onBarcodeScanned);
            });
    },

});

core.action_registry.add('mes_kiosk_mode', MesKioskMode);

return MesKioskMode;

});