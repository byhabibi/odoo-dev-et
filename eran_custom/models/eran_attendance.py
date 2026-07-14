from zk import ZK
import logging
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
import pytz
from datetime import datetime, timedelta, time
_logger = logging.getLogger(__name__)

class EranAttendanceMachineConfig(models.Model):
    _name = 'eran.attendance.machine.config'
    _description = 'Eran Attendance Machine Config'

    name = fields.Char('Nama Mesin')
    ip_address = fields.Char('IP Address', required=True)
    port = fields.Integer('Port', required=True)
    last_sync = fields.Text('Last Sync')
    connection_status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Connection Error')
    ], string='Status', default='offline', readonly=True)


    def action_test_connection(self):
        """ Fungsi untuk cek koneksi ke mesin X902 """
        for record in self:
            if not record.ip_address:
                raise UserError(_("Mohon isi IP Address terlebih dahulu!"))
            
            # Inisialisasi koneksi ZK
            zk = ZK(record.ip_address, port=record.port, timeout=5, password=0, force_udp=False, ommit_ping=False)
            conn = None
            try:
                # Coba hubungkan
                conn = zk.connect()
                # Jika berhasil sampai sini, update status
                record.write({
                    'connection_status': 'online',
                    'last_sync': fields.Datetime.now()
                })
                # Opsional: ambil nama mesin dari device
                # device_name = conn.get_device_name()
                
            except Exception as e:
                _logger.error(f"Koneksi Gagal ke {record.ip_address}: {str(e)}")
                record.write({'connection_status': 'error'})
                raise UserError(_("Koneksi Gagal: %s") % str(e))
            finally:
                if conn:
                    conn.disconnect()
        return True
    
    def action_disconnect(self):
        """ Fungsi untuk memutus status koneksi di Odoo """
        for record in self:
            record.write({
                'connection_status': 'offline'
            })
        return True

    def action_download_data(self):
        
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Jakarta')
        utc_tz = pytz.utc
        """ Fungsi untuk mendownload data log dari mesin X902 dan simpan ke model log transaksi """
        # SOLUSI UTAMA: Jika self kosong (karena dipanggil cron), cari semua mesin yang aktif
        records_to_process = self
        if not records_to_process:
            # Ganti 'state' atau field aktif sesuai field di model Anda (contoh: mengambil semua mesin)
            records_to_process = self.env['eran.attendance.machine.config'].search([]) 
            _logger.info("Cron mendeteksi self kosong. Memproses %s mesin ditemukan.", len(records_to_process))
        for record in records_to_process:
            if record.connection_status != 'online':
                raise UserError(_("Mesin tidak dalam status online. Mohon tes koneksi terlebih dahulu!"))
            
            zk = ZK(record.ip_address, port=record.port, timeout=10)
            conn = None
            try:
                conn = zk.connect()
                conn.disable_device()
                attendance_logs = conn.get_attendance()
                for log in attendance_logs:
                    machine_time = log.timestamp 
                    local_dt = user_tz.localize(machine_time, is_dst=None)
                    utc_dt_naive = local_dt.astimezone(utc_tz).replace(tzinfo=None)
                    str_utc_time = fields.Datetime.to_string(utc_dt_naive)
                    employee = self.env['hr.employee'].search([('pin', '=', str(log.user_id))], limit=1)

                    existing_log = self.env['eran.attendance.log.transaction'].search([
                            ('user_id', '=', log.user_id),
                            ('timestamp', '=', str_utc_time)
                        ], limit=1)

                    if not existing_log:
                        self.env['eran.attendance.log.transaction'].create({
                            'user_id': log.user_id,
                            'timestamp': str_utc_time,
                            'employee_id': employee.id if employee else False
                        })

                record.write({'last_sync': fields.Datetime.now()})
            except Exception as e:
                raise UserError(("Gagal Mendownload Data: %s") % str(e))
            finally:
                if conn: conn.disconnect()
        return True

    # def action_sync_attendance(self):
    #     user_tz = pytz.timezone(self.env.user.tz or 'Asia/Jakarta')
    #     utc_tz = pytz.utc

    #     for record in self:
    #         zk = ZK(record.ip_address, port=record.port, timeout=10)
    #         conn = None
    #         try:
    #             conn = zk.connect()
    #             conn.disable_device()
    #             attendance_logs = conn.get_attendance()
    #             # Urutkan ASC (paling pagi ke paling malam)
    #             sorted_logs = sorted(attendance_logs, key=lambda l: l.timestamp)
                
    #             for log in sorted_logs:
    #                 machine_time = log.timestamp 
    #                 local_dt = user_tz.localize(machine_time, is_dst=None)
    #                 utc_dt_naive = local_dt.astimezone(utc_tz).replace(tzinfo=None)
    #                 str_utc_time = fields.Datetime.to_string(utc_dt_naive)

    #                 employee = self.env['hr.employee'].search([('pin', '=', str(log.user_id))], limit=1)
    #                 if not employee or not employee.shift_id:
    #                     continue
                    
    #                 shift = employee.shift_id
    #                 hour_decimal = local_dt.hour + (local_dt.minute / 60.0)

    #                 # --- PROSES CHECK-IN (Data Pertama <= End Checkin) ---
    #                 if hour_decimal <= shift.end_checkin:
    #                     start_of_day = local_dt.replace(hour=0, minute=0, second=0).astimezone(utc_tz).replace(tzinfo=None)
                        
    #                     already_checkin = self.env['hr.attendance'].search([
    #                         ('employee_id', '=', employee.id),
    #                         ('check_in', '>=', fields.Datetime.to_string(start_of_day)),
    #                         ('check_in', '<=', str_utc_time)
    #                     ], limit=1)

    #                     if not already_checkin:
    #                         # Tutup absen menggantung sebelumnya jika ada (Constraint Odoo)
    #                         open_att = self.env['hr.attendance'].search([
    #                             ('employee_id', '=', employee.id),
    #                             ('check_out', '=', False)
    #                         ], limit=1)
    #                         if open_att:
    #                             open_att.write({'check_out': open_att.check_in})

    #                         self.env['hr.attendance'].create({
    #                             'employee_id': employee.id,
    #                             'check_in': str_utc_time,
    #                             'shift_id': shift.id,
    #                         })
    #                         self.env.cr.flush()

    #                 # --- PROSES CHECK-OUT (Data Pertama di rentang OR > End Checkout) ---
    #                 else:
    #                     # Cek apakah jam masuk dalam rentang Checkout normal ATAU sudah kelewat jauh (> End Checkout)
    #                     is_in_range = shift.start_checkout <= hour_decimal <= shift.end_checkout
    #                     is_after_range = hour_decimal > shift.end_checkout

    #                     if is_in_range or is_after_range:
    #                         # Cari absen masuk yang belum ada checkoutnya
    #                         open_attendance = self.env['hr.attendance'].search([
    #                             ('employee_id', '=', employee.id),
    #                             ('check_out', '=', False),
    #                             ('check_in', '<', str_utc_time)
    #                         ], limit=1, order='check_in desc')

    #                         if open_attendance:
    #                             # LOGIKA: Hanya update jika belum ada data checkout (Hanya ambil data pertama)
    #                             # Karena sorted_logs urut pagi->malam, maka data pertama yang masuk kriteria ini yang disimpan
    #                             open_attendance.write({'check_out': str_utc_time})
    #                             self.env.cr.flush()

    #             conn.enable_device()
    #             record.last_sync = fields.Datetime.now()
    #         except Exception as e:
    #             raise UserError(("Gagal Sinkronisasi: %s") % str(e))
    #         finally:
    #             if conn: conn.disconnect()
    #     return True
  
class eranAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Tambahan field untuk menyimpan info shift (optional)
    shift_id = fields.Many2one('eran.master.shift', string="Shift", readonly=True, compute="_compute_shift_id", store=True)
    overtime_id = fields.Many2one(
        'eran.hr.overtime', 
        string="Overtime", 
        store=True
    )
    checkin_lembur = fields.Datetime('Lembur Dari')
    checkout_lembur = fields.Datetime('Lembur Sampai')
    istirahat_lembur = fields.Float('Istirahat Lembur (Jam)')
    total_lembur = fields.Float('Total Lembur (Jam)', compute='_compute_total_lembur', store=True)

    @api.depends('check_in','check_out','employee_id')
    def _compute_shift_id(self):
        local_tz = pytz.timezone('Asia/Jakarta')
        utc_tz = pytz.utc

        for rec in self:
            if rec.shift_id:
                continue  # Jika shift_id sudah ada, lewati perhitungan

            if rec.check_in and rec.check_out and rec.employee_id:
                # Konversi check_in ke waktu lokal Jakarta
                utc_check_in = utc_tz.localize(rec.check_in)
                local_check_in = utc_check_in.astimezone(local_tz)
                local_date = local_check_in.date()

                
            else:
                rec.shift_id = False

    def float_to_time(self, float_hours):
        if not float_hours:
            return time(0, 0, 0)
        hours, remainder = divmod(float_hours, 1)
        minutes = remainder * 60
        return time(int(hours), int(round(minutes)), 0)

    def cron_sync_attendance_from_log(self):
        """ Fungsi otomatis untuk mencocokkan log mesin berdasarkan tipe jam kerja karyawan """
        local_tz = pytz.timezone('Asia/Jakarta')
        utc_tz = pytz.utc

        # 1. Ambil log transaksi mesin yang belum diproses
        logs = self.env['eran.attendance.log.transaction'].search([
            ('is_processed', '=', False)
        ], order='timestamp asc')

        for log in logs:
            # Peta karyawan berdasarkan PIN mesin
            if log.user_id == 53 or log.user_id == 22 or log.user_id == 21 or log.user_id == 89 or log.user_id == 124 or log.user_id == 23 or log.user_id == 25:
                if not log.employee_id:
                    employee = self.env['hr.employee'].search([('pin', '=', str(log.user_id))], limit=1)
                    if employee:
                        log.write({'employee_id': employee.id})
                    else:
                        continue
                else:
                    employee = log.employee_id

                # Konversi waktu log ke waktu lokal Jakarta
                utc_dt = utc_tz.localize(log.timestamp) #format dari database
                local_dt = utc_dt.astimezone(local_tz)  #format jam indonesia
                local_date = local_dt.date()
                hour_decimal = local_dt.hour + (local_dt.minute / 60.0)
                str_utc_time = fields.Datetime.to_string(log.timestamp)

                # Inisialisasi variabel batas toleransi absen
                start_checkin = None
                end_checkin = None
                start_checkout = None
                end_checkout = None

                # =================================================================
                # JALUR 1: JIKA KARYAWAN FLEXIBLE HOURS -> AMBIL DARI PLANNING.SLOT
                # =================================================================
                if employee.flexible_hours:  # Sesuaikan dengan nama field Boolean Anda di hr.employee
                    start_of_day = local_tz.localize(datetime.combine(local_date, datetime.min.time())).astimezone(utc_tz)
                    end_of_day = local_tz.localize(datetime.combine(local_date, datetime.max.time())).astimezone(utc_tz)

                    # start_date_str = f"{local_date} 00:00:00"
                    # end_date_str = f"{local_date} 23:59:59"
                    # Toleransi mundur ke hari kemarin jika log terjadi dini hari (antisipasi checkout shift malam)
                    # if local_dt.hour < 6:
                    #     local_date = local_date - timedelta(days=1)

                    start_date_str = fields.Datetime.to_string(start_of_day)
                    end_date_str = fields.Datetime.to_string(end_of_day)

                    planning_slot = self.env['planning.slot'].search([
                        ('employee_id', '=', employee.id),
                        ('start_datetime', '<=', start_date_str),
                        ('end_datetime', '>=', start_date_str),
                        ('state', '=', 'published')
                    ], limit=1, order='start_datetime asc')

                    if not planning_slot:
                        planning_slot = self.env['planning.slot'].search([
                                        ('employee_id', '=', employee.id),
                                        ('start_datetime', '<=', local_dt),
                                        ('end_datetime', '>=', local_dt),
                                        ('state', '=', 'published')
                                    ], limit=1, order='start_datetime asc')
                        if not planning_slot:
                            # 2. Buat range pencarian start dan end of day (00:00:00 sampai 23:59:59 waktu lokal)
                            # Lalu bersihkan timezone-nya (.replace(tzinfo=None)) agar siap masuk ke query Odoo
                            start_of_day_local = datetime.combine(local_date, datetime.min.time())
                            end_of_day_local = datetime.combine(local_date, datetime.max.time())

                            # Konversi balik range lokal tadi ke UTC untuk dicocokkan ke database planning.slot
                            start_of_day_utc = local_tz.localize(start_of_day_local).astimezone(utc_tz).replace(tzinfo=None)
                            end_of_day_utc = local_tz.localize(end_of_day_local).astimezone(utc_tz).replace(tzinfo=None)
                            planning_slot = self.env['planning.slot'].search([
                                                ('employee_id', '=', employee.id),
                                                ('start_datetime', '>=', start_of_day_utc),
                                                ('start_datetime', '<=', end_of_day_utc),
                                                ('state', '=', 'published')
                                            ], limit=1, order='start_datetime asc')
                            if not planning_slot:
                                continue

                    shift = planning_slot.shift_id
                    if shift:
                        t_start_checkin = self.float_to_time(shift.start_checkin)
                        t_end_checkin = self.float_to_time(shift.end_checkin)
                        t_start_checkout = self.float_to_time(shift.start_checkout)
                        t_end_checkout = self.float_to_time(shift.end_checkout)

                        # Skenario Keluar: Cek apakah jam selesai < jam mulai (artinya shift malam / lewat tengah malam)
                        if shift.end_time < shift.start_time:
                            # Jika shift malam, tanggal untuk checkout maju 1 hari dari tanggal absen masuk
                            checkout_start_date = local_date - timedelta(days=1)
                            checkout_end_date = local_date + timedelta(days=1)
                            slot_start_checkout = local_tz.localize(datetime.combine(checkout_start_date, t_start_checkout))
                            slot_end_checkout = local_tz.localize(datetime.combine(checkout_end_date, t_end_checkout))
                        else:
                            # Jika shift normal (di hari yang sama), tanggal checkout sama dengan tanggal absen masuk
                            slot_start_checkout = local_tz.localize(datetime.combine(local_date, t_start_checkout))
                            slot_end_checkout = local_tz.localize(datetime.combine(local_date, t_end_checkout))

                        # Menggabungkan tanggal dan waktu lokal ke objek datetime ber-timezone Jakarta
                        start_checkin = local_tz.localize(datetime.combine(local_date, t_start_checkin))
                        end_checkin = local_tz.localize(datetime.combine(local_date, t_end_checkin))
                        start_checkout = slot_start_checkout
                        end_checkout = slot_end_checkout
                    else:
                        continue
                        # 1. Pastikan planning_slot dikonversi ke waktu lokal terlebih dahulu untuk mengambil komponen 'time' yang asli
                        # slot_start_raw = pytz.utc.localize(planning_slot.start_datetime).astimezone(local_tz)
                        # slot_end_raw = pytz.utc.localize(planning_slot.end_datetime).astimezone(local_tz)

                        # # Ekstrak murni jam-menit-detik saja dari modul Planning
                        # time_start_planning = slot_start_raw.time()
                        # time_end_planning = slot_end_raw.time()

                        # # 2. GABUNGKAN: Tanggal diambil dari tanggal log mesin absen (local_date), Jam diambil dari Planning
                        # # Skenario Masuk: Menggunakan tanggal absen saat itu + jam dari planning
                        # slot_start_local = local_tz.localize(datetime.combine(local_date, time_start_planning))
                        # # Jika karyawan absen pulang di pagi hari (misal sebelum jam 09:00 pagi), 
                        # # maka HARI KERJA SEBENARNYA adalah HARI KEMARIN (Tanggal Masuk Shift Malam).
                        # if hour_decimal < 9.0:
                        #     real_work_date = local_dt.date() - timedelta(days=1)
                        # else:
                        #     real_work_date = local_dt.date()

                        # # Skenario Keluar: Cek apakah jam selesai < jam mulai (artinya shift malam / lewat tengah malam)
                        # if time_end_planning < time_start_planning:
                        #     # Jika shift malam, tanggal untuk checkout maju 1 hari dari tanggal absen masuk
                        #     checkout_date = real_work_date + timedelta(days=1)
                        #     slot_end_local = local_tz.localize(datetime.combine(checkout_date, time_end_planning))
                        # else:
                        #     # Jika shift normal (di hari yang sama), tanggal checkout sama dengan tanggal absen masuk
                        #     slot_end_local = local_tz.localize(datetime.combine(real_work_date, time_end_planning))

                        # # Set rentang toleransi (Contoh: 2 jam sebelum & sesudah)
                        # start_checkin = slot_start_local - timedelta(hours=2)
                        # end_checkin = slot_start_local + timedelta(hours=4)
                        # start_checkout = slot_end_local - timedelta(hours=5)
                        # end_checkout = slot_end_local + timedelta(hours=4)

                # =================================================================
                # JALUR 2: JIKA TIDAK FLEXIBLE -> AMBIL DARI shift_id di master employee
                # =================================================================
                else:
                    # Cari kalender kerja aktif dari kontrak karyawan
                    shift = employee.shift_id
                    if shift:
                        # konversi jam shift ke objek time
                        t_start_checkin = self.float_to_time(shift.start_checkin)
                        t_end_checkin = self.float_to_time(shift.end_checkin)
                        t_start_checkout = self.float_to_time(shift.start_checkout)
                        t_end_checkout = self.float_to_time(shift.end_checkout)
                        # Skenario Keluar: Cek apakah jam selesai < jam mulai (artinya shift malam / lewat tengah malam)
                        if shift.end_time < shift.start_time:
                            # Jika shift malam, tanggal untuk checkout maju 1 hari dari tanggal absen masuk
                            checkout_start_date = local_date - timedelta(days=1)
                            checkout_end_date = local_date + timedelta(days=1)
                            slot_start_checkout = local_tz.localize(datetime.combine(checkout_start_date, t_start_checkout))
                            slot_end_checkout = local_tz.localize(datetime.combine(checkout_end_date, t_end_checkout))
                        else:
                            # Jika shift normal (di hari yang sama), tanggal checkout sama dengan tanggal absen masuk
                            slot_start_checkout = local_tz.localize(datetime.combine(local_date, t_start_checkout))
                            slot_end_checkout = local_tz.localize(datetime.combine(local_date, t_end_checkout))

                        # Menggabungkan tanggal dan waktu lokal ke objek datetime ber-timezone Jakarta
                        start_checkin = local_tz.localize(datetime.combine(local_date, t_start_checkin))
                        end_checkin = local_tz.localize(datetime.combine(local_date, t_end_checkin))
                        start_checkout = slot_start_checkout
                        end_checkout = slot_end_checkout
                    else:
                        continue

                    

                # =================================================================
                # EKSEKUSI DATA ABSENSI ODOO (BERLAKU UNTUK KEDUA JALUR)
                # =================================================================
                if start_checkin and end_checkin and start_checkout and end_checkout:
                    
                    # --- LOGIKA PENENTUAN CHECK-IN ---
                    if start_checkin <= local_dt <= end_checkin:
                        day_start_utc = fields.Datetime.to_string(local_tz.localize(datetime.combine(local_date, datetime.min.time())).astimezone(utc_tz))
                        day_end_utc = fields.Datetime.to_string(local_tz.localize(datetime.combine(local_date, datetime.max.time())).astimezone(utc_tz))
                        already_checkin = self.env['hr.attendance'].search([
                            ('employee_id', '=', employee.id),
                            ('check_in', '>=', day_start_utc),
                            ('check_in', '<=', day_end_utc)
                        ], limit=1)

                        if not already_checkin:
                            open_att = self.env['hr.attendance'].search([
                                ('employee_id', '=', employee.id),
                                ('check_out', '=', False)
                            ], limit=1)
                            if open_att:
                                open_att.write({'check_out': open_att.check_in})

                            self.env['hr.attendance'].create({
                                'employee_id': employee.id,
                                'check_in': str_utc_time,
                                'shift_id': shift.id,
                            })
                            log.write({'is_processed': True})
                        else:
                            log.write({'is_processed': True}) # Opsional: tandai log selesai jika diperlukan
                            continue

                    # --- LOGIKA PENENTUAN CHECK-OUT ---
                    elif start_checkout <= local_dt <= end_checkout:
                        open_attendance = self.env['hr.attendance'].search([
                                        ('employee_id', '=', employee.id),
                                        ('check_in', '<', str_utc_time),
                                        '|', 
                                            ('check_out', '=', False), 
                                            ('check_out', '<', str_utc_time)
                                    ], limit=1, order='check_in desc')

                        if open_attendance:
                            open_attendance.write({'check_out': str_utc_time})
                        log.write({'is_processed': True})
                    
                    else:
                        continue

        self.env.cr.flush()
        return True

    @api.depends('checkin_lembur', 'checkout_lembur', 'istirahat_lembur')
    def _compute_total_lembur(self):
        for rec in self:
            if rec.checkin_lembur and rec.checkout_lembur:
                total_seconds = (rec.checkout_lembur - rec.checkin_lembur).total_seconds()
                total_hours = total_seconds / 3600.0
                rec.total_lembur = max(total_hours - rec.istirahat_lembur, 0)
            else:
                rec.total_lembur = 0
  


class eranAttendanceLog(models.Model):
    _name = 'eran.attendance.log.transaction'
    _description = 'Log Transaksi Absen Mesin'
    _order = 'timestamp desc' # Agar data terbaru muncul di atas

    user_id = fields.Integer('User ID mesin')
    employee_id = fields.Many2one('hr.employee', string="employee")
    timestamp = fields.Datetime('Timestamp')
    is_processed = fields.Boolean(string="Processed", default=False)

class eranplanningSlot(models.Model):
    _inherit = 'planning.slot'

    # Tambahan field untuk menyimpan info shift (optional)
    shift_id = fields.Many2one('eran.master.shift', string="Shift", compute='_compute_actual_times', store=True)
    actual_start = fields.Datetime('Actual Start', readonly=True, compute='_compute_actual_times', store=True)
    actual_end = fields.Datetime('Actual End', readonly=True, compute='_compute_actual_times', store=True)

    @api.depends('start_datetime', 'end_datetime')
    def _compute_actual_times(self):
        local_tz = pytz.timezone('Asia/Jakarta')
        utc_tz = pytz.utc

        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                # Konversi waktu dari UTC ke Waktu Lokal Jakarta
                utc_start = utc_tz.localize(slot.start_datetime)
                utc_end = utc_tz.localize(slot.end_datetime)
                local_start = utc_start.astimezone(local_tz)
                local_end = utc_end.astimezone(local_tz)

                slot.actual_start = slot.start_datetime
                slot.actual_end = slot.end_datetime

                # Ekstrak murni jam-menit-detik saja dari modul Planning
                time_start_planning = local_start.hour + (local_start.minute / 60.0)
                time_end_planning = local_end.hour + (local_end.minute / 60.0)

                shift = self.env['eran.master.shift'].search([('start_time', '=', time_start_planning), ('end_time', '=', time_end_planning)], limit=1)
                slot.shift_id = shift.id if shift else False

class eranAttendanceOvertime(models.Model):
    _name = 'eran.hr.overtime'
    _description = 'attendance overtime'
    _order = 'tanggal_pengajuan desc' # Agar data terbaru muncul di atas
    _inherit = ['mail.thread', 'mail.activity.mixin'] 

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting Approval'),
        ('done', 'Done'),
        ('closed', 'Closed')
    ]
    name = fields.Char('Nama Document', default='New')
    tanggal_pengajuan = fields.Date('Tanggal Pengajuan')
    state = fields.Selection(STATE_SELECTION, string='State', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # APPROVAL 
    approval_line_ids = fields.One2many('eran.attendance.overtime.approval.line', 'overtime_id', string="Approval Line", )
    approval_attendance_overtime_id = fields.Many2one('mans.approval.hr', string="Approval HR", compute="_compute_approval_attendance_overtime_id")
    approval_rule = fields.Selection(related="approval_attendance_overtime_id.approval_rule", string="Approval Rule")
    approval_type = fields.Selection(related="approval_attendance_overtime_id.approval_type", string="Approval Type")
    models = fields.Selection(related="approval_attendance_overtime_id.models", string="Model")
    assigned_to_ids = fields.Many2many(comodel_name="res.users",string="Approver",)
    user_in_assigned_to = fields.Boolean(string="User Is Assigned", compute="_computed_user_in_assigned_to")

    # Attendance Overtime Line
    attendance_overtime_line = fields.One2many('eran.hr.overtime.line', 'overtime_id', 'Attendance Overtime Line', copy=True)

    def btn_draft(self):
        self.state = 'draft'

    def btn_waiting_approval(self):
        # set approver
        records = []
        is_sunday = False
        if self.tanggal_pengajuan:
            date = fields.Date.from_string(self.tanggal_pengajuan)
            is_sunday = date.weekday() == 6
        if self.env.user.sudo().employee_id.approver_ids:
            for appr_line in self.approval_attendance_overtime_id:
                if appr_line.approval_type == 'position-base-approval':
                    for job in appr_line.job_ids:
                        for approver in self.env.user.sudo().employee_id.approver_ids:
                            if job.job_id.id == approver.job_id.id:
                                records.append(approver.user_id.id)
                                if is_sunday:
                                    self.env['eran.attendance.overtime.approval.line'].create({
                                        'overtime_id': self.id,
                                        'user_id': approver.user_id.id,
                                    })
                                else:
                                    president_director = job.job_id.name == 'PRESIDEN DIRECTOR'
                                    if not president_director:
                                        self.env['eran.attendance.overtime.approval.line'].create({
                                            'overtime_id': self.id,
                                            'user_id': approver.user_id.id,
                                        })

                else:
                    for user in appr_line.user_ids:
                        records.append(user.user_id.id)
                        self.env['eran.attendance.overtime.approval.line'].create({
                                'overtime_id': self.id,
                                'user_id': user.user_id.id,
                            })
        
        if not self.env.user.sudo().employee_id.approver_ids or len(records) == 0:
            raise ValidationError(_("Can't find approver for current user!"))

        self.assigned_to_ids = [(6, 0, records)]
        activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'eran.hr.overtime')], limit=1).id

        # send notification 
        if self.approval_rule == 'only-one-approved':
            # send notification to the first approver
            for rec in records:
                self.send_mail_activity(activity_type_id, rec, self.id, res_model_id)
        else:
            # send notification to all approver
            self.send_mail_activity(activity_type_id, records[0], self.id, res_model_id)

        # set state
        self.write({'state':'waiting_approval'})
    
    def send_mail_activity(self, activity_type_id, user_id, res_id, res_model_id):
        self.env["mail.activity"].sudo().create(
            {
                "activity_type_id": activity_type_id,
                "note": _(
                    "You have employees in the Attendance Overtime document that you need to approve "
                    "Check if an action is needed."
                ),
                "user_id": (
                    user_id
                ),
                "res_id": res_id,
                "res_model_id": res_model_id,
                'summary': 'Reminder Attendance Overtime Approval',
            }
        )

    def btn_approved(self):
        # set approval
        approval_attendance_overtimen = self.env['eran.attendance.overtime.approval.line']
        # set is approved
        record = approval_attendance_overtimen.search([('overtime_id', '=', self.id), ('user_id', '=', self.env.user.id),('is_approved', '=', False)], limit=1)
        record.write({'is_approved': True, 'date_approved': datetime.now()})
        
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'eran.hr.overtime')], limit=1).id

        # set state
        if self.approval_rule == 'only-one-approved':
            # self.active_approver = self.assigned_to_ids
            if any(self.approval_line_ids.mapped('is_approved')):
                self.write({'state':'done'})
                # set all mail activity to be done
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).action_done()
                self._compute_to_attendance()
        # set state
        else:
            is_approved_counted = len(approval_attendance_overtimen.search([('is_approved', '=', True), ('overtime_id.models', '=', 'overtime'), ('overtime_id', '=', self.id)]).ids)
            approval_attendance_overtimen_user = [rec.user_id for rec in approval_attendance_overtimen.search([], order='id asc')]
            current_user_id = approval_attendance_overtimen_user[is_approved_counted - 1] if is_approved_counted else approval_attendance_overtimen_user[0]

            if all(self.approval_line_ids.mapped('is_approved')):
                self.write({'state':'done'})
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                self._compute_to_attendance()
            else:
                # assign to the next approver
                user_id = approval_attendance_overtimen_user[is_approved_counted]

                # set mail activity to be done one by one
                self.env["mail.activity"].sudo().search([('res_id', '=', self.id),('res_model_id', '=', res_model_id),('user_id', '=', current_user_id.id)]).action_done()
                activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
                
                # send notification to the next approver
                self.send_mail_activity(activity_type_id, user_id.id, self.id, res_model_id)

    
    def btn_set_to_draft(self):
        # ulink mail activity
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'eran.hr.overtime')], limit=1).id
        self.env["mail.activity"].sudo().search([('res_id', '=', self.id), ('res_model_id', '=', res_model_id)]).unlink()
        # reset assigned_to_ids
        self.assigned_to_ids = [(6, 0, [])]
        # reset approval line
        self.env['eran.attendance.overtime.approval.line'].search([('overtime_id', '=', self.id)]).unlink()
        # set state
        self.write({'state':'draft'})

    def _compute_approval_attendance_overtime_id(self):
        for rec in self:
            rec.approval_attendance_overtime_id = self.env['mans.approval.hr'].search([('models', '=', 'attendance_overtime')], limit=1).id

    def _computed_user_in_assigned_to(self):
        if self.assigned_to_ids and self.state == 'waiting_approval':
            if self.approval_rule == 'only-one-approved':
                self.user_in_assigned_to = True if self.env.user.id in self.assigned_to_ids.ids else False
            else:
                for appr in self.approval_line_ids:
                    if appr.is_approved:
                        continue
                    else:
                        self.user_in_assigned_to = True if self.env.user.id == appr.user_id.id else False
                        break
        else:
            self.user_in_assigned_to = False


    def _compute_to_attendance(self):
        """ Fungsi ini dipanggil dari btn_approved saat status berubah jadi 'done' """
        # Ambil timezone user atau default Asia/Jakarta
        user_tz = self.env.user.tz or 'Asia/Jakarta'
        local_tz = pytz.timezone(user_tz)

        for rec in self:
            # Karena dipanggil di dalam btn_approved setelah write state='done', 
            # kondisi rec.state == 'done' sudah pasti terpenuhi.
            if rec.attendance_overtime_line:
                
                for line in rec.attendance_overtime_line:
                    # Validasi kelengkapan data sebelum diproses
                    if not line.tanggal_pengajuan or line.start_actual is False or line.finish_actual is False:
                        continue

                    # --- 1. AMBIL RENTANG WAKTU LOKAL (AWAL & AKHIR HARI) ---
                    # Gabungkan tanggal dengan jam minimal (00:00:00) dan maksimal (23:59:59)
                    dt_start_local = datetime.combine(line.tanggal_pengajuan, datetime.min.time())
                    dt_end_local = datetime.combine(line.tanggal_pengajuan, datetime.max.time())

                    # Konversi rentang waktu lokal tersebut ke UTC untuk kueri ORM
                    dt_start_utc = local_tz.localize(dt_start_local).astimezone(pytz.utc).replace(tzinfo=None)
                    dt_end_utc = local_tz.localize(dt_end_local).astimezone(pytz.utc).replace(tzinfo=None)

                    # --- 2. CARI ATTENDANCE MENGGUNAKAN ORM ODOO ---
                    # Menggunakan ORM dengan nilai datetime UTC hasil konversi tadi
                    attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', line.employee_id.id),
                        ('check_in', '>=', fields.Datetime.to_string(dt_start_utc)),
                        ('check_in', '<=', fields.Datetime.to_string(dt_end_utc))
                    ], limit=1)

                    # --- 3. PROSES DATA JIKA ABSENSI DITEMUKAN ---
                    if attendance:
                        # Konversi jam float untuk kebutuhan write datetime di Odoo
                        start_hours, start_minutes = divmod(line.start_actual * 60, 60)
                        finish_hours, finish_minutes = divmod(line.finish_actual * 60, 60)

                        # Buat datetime lokal awal berdasarkan input jam float lembur
                        dt_checkin_local = datetime.combine(line.tanggal_pengajuan, datetime.min.time()) + timedelta(hours=int(start_hours), minutes=int(start_minutes))
                        dt_checkout_local = datetime.combine(line.tanggal_pengajuan, datetime.min.time()) + timedelta(hours=int(finish_hours), minutes=int(finish_minutes))

                        # Handle jika jam lembur selesai melewati tengah malam (keesokan harinya)
                        if line.finish_actual < line.start_actual:
                            dt_checkout_local += timedelta(days=1)

                        # Konversi hasil akhir jam lembur lokal ke UTC sebelum di-write ke database
                        dt_checkin_utc = local_tz.localize(dt_checkin_local).astimezone(pytz.utc).replace(tzinfo=None)
                        dt_checkout_utc = local_tz.localize(dt_checkout_local).astimezone(pytz.utc).replace(tzinfo=None)

                        # Tulis data lembur ke record absensi yang ditemukan
                        attendance.write({
                            'overtime_id': rec.id,
                            'checkin_lembur': dt_checkin_utc,
                            'checkout_lembur': dt_checkout_utc,
                            'istirahat_lembur': line.istirahat_actual,
                        })

                    else:
                        # Jika absensi tidak ditemukan, munculkan pesan error agar transaksi tidak menggantung
                        raise ValidationError(_("Gagal memproses lembur! Data absensi untuk karyawan %s pada tanggal %s tidak ditemukan di sistem.") % (line.employee_id.name, line.tanggal_pengajuan))
            else:
                raise ValidationError(_("Gagal memproses! Dokumen overtime tidak memiliki baris data (lines)."))

class EranAttendanceOvertimeApprovalLine(models.Model):
    _name = 'eran.attendance.overtime.approval.line'
    _description = 'Attendance Overtime Approval Line'

    overtime_id = fields.Many2one('eran.hr.overtime', string='Overtime', ondelete='cascade')
    is_approved = fields.Boolean(string="Is Approved")
    date_approved = fields.Datetime(string="Date Approved")
    user_id = fields.Many2one('res.users', string="User")    
    signature = fields.Binary(related='user_id.employee_id.signature', string="Signature")

class eranAttendanceOvertimeLine(models.Model):
    _name = 'eran.hr.overtime.line'
    _description = 'attendance overtime line'

    overtime_id = fields.Many2one('eran.hr.overtime', "overtime",
        required=True, ondelete='cascade', index=True, copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    start_plan = fields.Float('Start Plan')
    finish_plan = fields.Float('Finish Plan')
    istirahat_plan = fields.Float('Istirahat Plan')
    durasi_plan = fields.Float('Durasi Plan', compute='_compute_durasi_plan')
    start_actual = fields.Float('Start Actual')
    finish_actual = fields.Float('Finish Actual')
    istirahat_actual = fields.Float('Istirahat Actual')
    durasi_actual = fields.Float('Durasi Actual', compute='_compute_durasi_actual')
    tanggal_pengajuan = fields.Date(
        related='overtime_id.tanggal_pengajuan', 
        string='Tanggal Pengajuan', 
        store=True, 
        index=True)

    company_id = fields.Many2one(
        related='overtime_id.company_id',
        store=True, index=True, precompute=True)
    

    @api.depends('start_plan', 'finish_plan', 'istirahat_plan')
    def _compute_durasi_plan(self):
        for rec in self:
            if rec.start_plan and rec.finish_plan:
                rec.durasi_plan = rec.finish_plan - rec.start_plan - rec.istirahat_plan
            else:
                rec.durasi_plan = 0

    @api.depends('start_actual', 'finish_actual', 'istirahat_actual')
    def _compute_durasi_actual(self):
        for rec in self:
            if rec.start_actual and rec.finish_actual:
                rec.durasi_actual = rec.finish_actual - rec.start_actual - rec.istirahat_actual
            else:
                rec.durasi_actual = 0


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def attendance_scan(self, barcode):

        _logger.warning("========== BARCODE SCAN ==========")
        _logger.warning("Barcode : %s", barcode)
        _logger.warning("==================================")


        # ===================================
        # Cari Employee
        # ===================================
        employee = self.sudo().search([
            ("barcode", "=", barcode)
        ], limit=1)

        if not employee:
            _logger.warning("Employee tidak ditemukan")
            return super().attendance_scan(barcode)

        _logger.warning("Employee : %s", employee.name)
        _logger.warning("Employee ID : %s", employee.id)

        # ===================================
        # Jalankan Attendance bawaan Odoo
        # ===================================
        result = super().attendance_scan(barcode)

        # ===================================
        # Attendance terbaru
        # ===================================
        attendance = self.env["hr.attendance"].sudo().search([
            ("employee_id", "=", employee.id)
        ], order="id desc", limit=1)

        if not attendance:
            _logger.warning("Attendance tidak ditemukan")
            return result

        today = attendance.check_in.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        _logger.warning("================ DATE FILTER ================")
        _logger.warning("Check In : %s", attendance.check_in)
        _logger.warning("Today    : %s", today)
        _logger.warning("Tomorrow : %s", tomorrow)
        _logger.warning("============================================")

        # ===================================
        # Cari Work Order: OPERATOR + TANGGAL saja
        # ===================================
        domain = [
            ("operator_id", "=", employee.id),
            ("state", "in", ["pending", "waiting", "ready", "progress", "done"]),
            ("production_id.date_planned_start", ">=", today),
            ("production_id.date_planned_start", "<", tomorrow),
        ]

        _logger.warning("DOMAIN WORKORDER = %s", domain)

        workorders = self.env["mrp.workorder"].sudo().search(domain)

        _logger.warning("TOTAL WO DITEMUKAN = %s", len(workorders))

        for wo in workorders:
            _logger.warning(
                "WO_ID=%s | WO=%s | MO=%s | WC=%s | STATE=%s",
                wo.id,
                wo.name,
                wo.production_id.name,
                wo.workcenter_id.name,
                wo.state
            )

        if not workorders:
            _logger.warning("Tidak ada Work Order yang cocok untuk employee ini hari ini")
            return result

        # ===================================
        # Buat Approval + Lines
        # ===================================
        approval = self.env["mes.scan.approval"].sudo().create({
            "employee_id": employee.id,
            "check_in": attendance.check_in,
            "scan_time": fields.Datetime.now(),
            "shift_id": workorders[:1].shift_id.id,
            "workcenter_id": workorders[:1].workcenter_id.id,
            "state": "ready",
        })

        _logger.warning("APPROVAL ID = %s", approval.id)

        STATE_MAP = {
            "pending": "ready",
            "waiting": "ready",
            "ready": "ready",
            "progress": "running",
            "done": "done",
        }

        for seq, wo in enumerate(workorders, start=1):

            line = self.env["mes.scan.approval.line"].sudo().create({
                "approval_id": approval.id,
                "sequence": seq,
                "workorder_id": wo.id,
                "qty_target": wo.production_id.product_qty,
                "qty_actual": 0,
                "state": STATE_MAP.get(wo.state, "ready"),
            })

            _logger.warning("LINE %s CREATED, ID = %s | WO = %s | STATE = %s", seq, line.id, wo.name, line.state)

        _logger.warning("FINISH CREATE APPROVAL")

        return result
    
class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    # Field tambahan untuk ditampilkan di tabel Work Order
    employee_id = fields.Many2one('hr.employee', string="Operator")
    shift_id = fields.Many2one('eran.master.shift', string="Shift")

    def button_start(self):
        # 1. Jalankan fungsi standar Odoo
        res = super(MrpWorkorder, self).button_start()
        
        # 2. Ambil data scan approval terbaru yang statusnya 'approved'
        last_scan = self.env['mes.scan.approval'].search([
            ('state', '=', 'approved')
        ], order='scan_time desc', limit=1)
        
        # 3. Otomatis isi ke Work Order saat tombol start diklik
        if last_scan:
            self.write({
                'employee_id': last_scan.employee_id.id,
                'shift_id': last_scan.shift_id.id
            })
        return res