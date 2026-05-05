const WebSocket = require('ws');

console.log('WebSocket Test Client Starting...\n');

// Test URLs
const threadId = 'test_thread_123';
const token = 'test-token'; // Test token for backend
const urls = [
    `ws://127.0.0.1:8000/api/chats/${threadId}/ws?token=${encodeURIComponent(token)}`,
    `ws://localhost:8000/api/chats/${threadId}/ws?token=${encodeURIComponent(token)}`,
    `ws://127.0.0.1:8000/ws`,
    `ws://localhost:8000/ws`,
    `ws://127.0.0.1:8000/api/chats/ws?thread=${threadId}`
];

async function testUrl(url, index) {
    return new Promise((resolve) => {
        console.log(`${index + 1}. Testing: ${url}`);

        const ws = new WebSocket(url, {
            handshakeTimeout: 5000,
            perMessageDeflate: false
        });

        const timeout = setTimeout(() => {
            console.log(`   ✗ Timeout after 5 seconds`);
            ws.close();
            resolve(false);
        }, 5000);

        ws.on('open', () => {
            clearTimeout(timeout);
            console.log(`   ✓ Connected successfully!`);
            console.log(`   Sending test message...`);

            // Send a test message in the format expected by backend
            const testMessage = {
                type: 'message',
                text: 'Hello from test client!',
                user_id: 'e53439c1-cec2-45ab-8854-9e13efda26e3', // Valid UUID
                id: 'test-msg-' + Date.now()
            };

            ws.send(JSON.stringify(testMessage));
        });

        ws.on('message', (data) => {
            console.log(`   📨 Received: ${data.toString()}`);
        });

        ws.on('close', (code, reason) => {
            clearTimeout(timeout);
            const reasonStr = reason.toString();
            console.log(`   🔌 Closed with code ${code}${reasonStr ? `, reason: ${reasonStr}` : ''}`);

            if (code === 1011) {
                console.log(`   ⚠️  Code 1011 = Internal Server Error - Backend issue!`);
            }

            resolve(code === 1011 ? 'server_error' : code === 1000 ? 'normal_close' : 'other');
        });

        ws.on('error', (error) => {
            clearTimeout(timeout);
            console.log(`   ✗ Error: ${error.message}`);
            resolve(false);
        });
    });
}

async function runTests() {
    console.log('Testing WebSocket connections...\n');

    for (let i = 0; i < urls.length; i++) {
        const result = await testUrl(urls[i], i);
        console.log('');

        // Small delay between tests
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log('Test completed!');
    console.log('\nRecommendations:');
    console.log('1. If all connections fail with ECONNREFUSED - backend server not running');
    console.log('2. If connections succeed but close with 1011 - backend WebSocket endpoint has issues');
    console.log('3. If connections succeed and stay open - WebSocket works!');
    console.log('4. Check backend logs for WebSocket connection attempts');

    process.exit(0);
}

runTests().catch(console.error);