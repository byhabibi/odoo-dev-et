/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import MainComponent from '@stock_barcode/components/main';

patch(MainComponent.prototype, 'custom_stock_barcode.MainComponent', {
    get displayBarcodeLines() {
        return this.displayBarcodeApplication && (this.env.model.canBeProcessed || this.env.model.isDone);
    },
});

patch(BarcodePickingModel.prototype, 'custom_stock_barcode.BarcodePickingModel', {
    get isDone() {
        return this.record.state === 'done' || this.record.state_dn_out === 'done';
    },

    get canBeValidate() {
        if (this.isDone || this.isCancelled) {
            return false;
        }
        if (this.record.immediate_transfer) {
            return super.canBeValidate; // For immediate transfers, doesn't care about any special condition.
        } else if (!this.config.barcode_validation_full && !this.currentState.lines.some(line => line.qty_done)) {
            return false; // Can't be validate because "full validation" is forbidden and nothing was processed yet.
        }
        return super.canBeValidate;
    },

    get canPutInPack() {
        if (this.isDone || this.isCancelled) {
            return false;
        }
        if (this.config.restrict_scan_product) {
            return this.pageLines.some(line => line.qty_done && !line.result_package_id);
        }
        return true;
    },
});