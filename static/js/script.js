// static/js/main.js

// QR Code Generation
function generateQRCode(ticketData) {
    const qr = new QRCode(document.getElementById("qrcode"), {
        text: ticketData,
        width: 256,
        height: 256,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });
}

// Ticket Generation
document.getElementById('generateForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            generateQRCode(data.ticket_id);
            document.getElementById('downloadBtn').classList.remove('hidden');
            document.getElementById('ticketResult').classList.remove('hidden');
            document.getElementById('ticketId').textContent = data.ticket_id;
        } else {
            alert('Error generating ticket: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate ticket');
    }
});

// QR Code Scanner
let scanner = null;

async function initializeScanner() {
    try {
        scanner = new Html5QrcodeScanner("reader", {
            qrbox: {
                width: 250,
                height: 250
            },
            fps: 20
        });

        scanner.render(onScanSuccess, onScanFailure);
    } catch (error) {
        console.error('Scanner initialization failed:', error);
        alert('Failed to initialize scanner. Please check camera permissions.');
    }
}

async function onScanSuccess(decodedText) {
    try {
        const response = await fetch('/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ticket_id: decodedText
            })
        });

        const data = await response.json();
        
        const resultDiv = document.getElementById('scanResult');
        resultDiv.innerHTML = `
            <div class="alert ${data.valid ? 'alert-success' : 'alert-danger'}">
                <h4>${data.valid ? 'Valid Ticket' : 'Invalid Ticket'}</h4>
                <p>${data.message}</p>
                ${data.valid ? `<p>Ticket ID: ${decodedText}</p>` : ''}
            </div>
        `;
        
        // Stop scanning after successful scan
        if (data.valid) {
            scanner.clear();
            // Restart scanner after 3 seconds
            setTimeout(() => {
                resultDiv.innerHTML = '';
                initializeScanner();
            }, 3000);
        }
    } catch (error) {
        console.error('Verification failed:', error);
        alert('Failed to verify ticket');
    }
}

function onScanFailure(error) {
    // Handle scan failure silently
    console.warn(`QR Code scanning failed: ${error}`);
}

// Download Ticket
document.getElementById('downloadBtn')?.addEventListener('click', async () => {
    const ticketId = document.getElementById('ticketId').textContent;
    try {
        const response = await fetch(`/download/${ticketId}`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ticket-${ticketId}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to download ticket');
        }
    } catch (error) {
        console.error('Download failed:', error);
        alert('Failed to download ticket');
    }
});

// Initialize scanner if on scan page
if (document.getElementById('reader')) {
    initializeScanner();
}

// Dark mode toggle
const darkModeToggle = document.getElementById('darkModeToggle');
if (darkModeToggle) {
    darkModeToggle.addEventListener('click', () => {
        document.documentElement.classList.toggle('dark');
        const isDark = document.documentElement.classList.contains('dark');
        localStorage.setItem('darkMode', isDark);
    });

    // Check for saved dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        document.documentElement.classList.add('dark');
    }
}

// Copy Ticket ID
document.getElementById('copyBtn')?.addEventListener('click', () => {
    const ticketId = document.getElementById('ticketId').textContent;
    navigator.clipboard.writeText(ticketId)
        .then(() => {
            alert('Ticket ID copied to clipboard!');
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            alert('Failed to copy ticket ID');
        });
});
