const https = require('https');

const data = JSON.stringify({
    professional_id: 'c14e1a0b-1188-44d4-9d58-96c21e6466f9',
    customer_name: 'Test',
    customer_phone: '5597991728899',
    start_time: '2026-06-21T10:00:00Z',
    otp_code: '1234'
});

const options = {
    hostname: 'agendamentos01-production.up.railway.app',
    port: 443,
    path: '/appointments',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length
    }
};

const req = https.request(options, res => {
    let result = '';
    res.on('data', d => { result += d; });
    res.on('end', () => { console.log('Status:', res.statusCode, 'Body:', result); });
});

req.on('error', error => { console.error('Error:', error); });
req.write(data);
req.end();
