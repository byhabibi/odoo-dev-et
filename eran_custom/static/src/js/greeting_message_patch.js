odoo.define('eran_custom.greeting_message_patch', function (require) {
"use strict";

var GreetingMessage = require('hr_attendance.greeting_message');
var core = require('web.core');
var _t = core._t;

GreetingMessage.include({

    welcome_message: function () {
        // ===== Ganti seluruh pesan welcome dengan versi custom =====
        this.$('.o_hr_attendance_message_message').append(_t("Semoga harimu menyenangkan, selamat datang di PT. Eran!"));
        this.$('.o_hr_attendance_random_message').html(_t("Jangan lupa scan badge di dekat mesin sebelum mulai kerja."));

        // Tetap jalankan auto-close timer seperti aslinya
        var self = this;
        if (this.kioskDelay > 0) {
            this.return_to_main_menu = setTimeout(function () {
                self.do_action(self.next_action, { clear_breadcrumbs: true });
            }, this.kioskDelay);
        }
    },

    farewell_message: function () {
        // ===== Ganti seluruh pesan farewell dengan versi custom =====
        this.$('.o_hr_attendance_message_message').append(_t("Terima Kasih"));
        this.$('.o_hr_attendance_random_message').html(_t("Sampai jumpa besok!"));

        var self = this;
        if (this.kioskDelay > 0) {
            this.return_to_main_menu = setTimeout(function () {
                self.do_action(self.next_action, { clear_breadcrumbs: true });
            }, this.kioskDelay);
        }
    },

});

return GreetingMessage;

});