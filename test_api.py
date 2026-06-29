import urllib.request
import urllib.error
import json

url = 'https://agendamentos01-production.up.railway.app/appointments'
data = {
    'professional_id': 'c14e1a0b-1188-44d4-9d58-96c21e6466f9',
    'customer_name': 'Test',
    'customer_phone': '5597991728899',
    'start_time': '2026-06-21T10:00:00Z',
    'otp_code': '1234'
}
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print('Success:', response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTPError:', e.code)
    print('Reason:', e.read().decode('utf-8'))
except Exception as e:
    print('Error:', str(e))
