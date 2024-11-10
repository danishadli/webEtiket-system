from flask import Flask, render_template, request, jsonify, send_file
import cv2
from pyzbar.pyzbar import decode
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import qrcode
import os
import json
import pandas as pd
from PIL import Image
import io

app = Flask(__name__)

# Konfigurasi Google Sheets
SCOPE = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
CREDS = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
CLIENT = gspread.authorize(CREDS)

# Ganti dengan nama spreadsheet Anda
SPREADSHEET = CLIENT.open_by_key('1YiD-zAfYyxWunB8EeuxLC_uWeiryDL6D9EKnIhER7LQ')
WORKSHEET = SPREADSHEET.sheet1

def refresh_google_auth():
    """Refresh Google auth jika expired"""
    global CLIENT, WORKSHEET
    if CREDS.access_token_expired:
        CLIENT = gspread.authorize(CREDS)
        WORKSHEET = SPREADSHEET.sheet1

class TicketManager:
    @staticmethod
    def generate_ticket_id():
        """Generate unique ticket ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"T{timestamp}"

    @staticmethod
    def create_qr_code(ticket_id, additional_data=None):
        """Create QR code with ticket data"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Combine ticket_id with additional data if provided
        qr_data = {
            'ticket_id': ticket_id,
            'generated_at': datetime.now().isoformat()
        }
        if additional_data:
            qr_data.update(additional_data)
            
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        return qr.make_image(fill_color="black", back_color="white")

    @staticmethod
    def save_to_spreadsheet(ticket_data):
        """Save ticket data to Google Spreadsheet"""
        refresh_google_auth()
        try:
            row = [
                ticket_data['ticket_id'],
                ticket_data['nama'],
                ticket_data['email'],
                ticket_data.get('kategori', ''),  # Default if 'kategori' is missing
                'Belum Hadir',  # Status awal
                '',  # Waktu check-in
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Waktu generate
            ]
            
            # Debugging untuk melihat data yang dimasukkan
            print(f"Appending row: {row}")  # Debugging untuk lihat row
            WORKSHEET.append_row(row)  # Menambahkan row ke sheet
            
            return True
        except Exception as e:
            print(f"Error saving to spreadsheet: {str(e)}")
            return False

class TicketVerifier:
    @staticmethod
    def verify_ticket(ticket_id):
        """Verify ticket and update attendance"""
        refresh_google_auth()
        try:
            # Find ticket in spreadsheet
            cell = WORKSHEET.find(ticket_id)
            if not cell:
                return {'status': 'error', 'message': 'Tiket tidak ditemukan'}

            row_values = WORKSHEET.row_values(cell.row)
            
            # Check if ticket already used
            if row_values[4] == 'Hadir':
                return {
                    'status': 'already_checked',
                    'message': 'Tiket sudah digunakan',
                    'check_in_time': row_values[5]
                }

            # Update attendance
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            WORKSHEET.update_cell(cell.row, 5, 'Hadir')
            WORKSHEET.update_cell(cell.row, 6, now)

            return {
                'status': 'success',
                'message': 'Check-in berhasil',
                'nama': row_values[1],
                'email': row_values[2],
                'kategori': row_values[3],
                'check_in_time': now
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate')
def generate():
    return render_template('generate.html')

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/api/generate-ticket', methods=['POST'])
def generate_ticket():
    try:
        data = request.form.to_dict()
        ticket_id = TicketManager.generate_ticket_id()
        
        # Add ticket_id to data
        data['ticket_id'] = ticket_id
        
        # Generate QR Code
        qr_image = TicketManager.create_qr_code(ticket_id, {
            'nama': data['nama'],
            'email': data['email']
        })
        
        # Save to spreadsheet
        if not TicketManager.save_to_spreadsheet(data):
            return jsonify({
                'success': False,
                'message': 'Gagal menyimpan data tiket'
            })
        
        # Save QR code to memory
        img_byte_arr = io.BytesIO()
        qr_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Save QR code to file system
        qr_path = f"static/qrcodes/{ticket_id}.png"
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        qr_image.save(qr_path)
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'qr_path': qr_path
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/api/verify-ticket', methods=['POST'])
def verify_ticket():
    try:
        data = request.json
        ticket_data = json.loads(data['ticket_data'])
        result = TicketVerifier.verify_ticket(ticket_data['ticket_id'])
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

@app.route('/api/get-attendance', methods=['GET'])
def get_attendance():
    refresh_google_auth()
    try:
        # Get all records from spreadsheet
        records = WORKSHEET.get_all_records()
        return jsonify({
            'success': True,
            'data': records
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    # Ensure qrcodes directory exists
    os.makedirs('static/qrcodes', exist_ok=True)
    app.run(debug=True)
