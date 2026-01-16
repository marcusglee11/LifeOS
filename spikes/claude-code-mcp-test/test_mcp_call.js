const { spawn } = require('child_process');

const server = spawn('npx', ['claude-code-mcp'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true
});

let buffer = '';

server.stdout.on('data', (data) => {
    buffer += data.toString();
    // Try to parse complete JSON-RPC messages
    const lines = buffer.split('\n');
    // Process all lines except the last one which might be incomplete
    for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i];
        if (line.trim()) {
            try {
                const msg = JSON.parse(line);
                console.log('RESPONSE:', JSON.stringify(msg, null, 2));
            } catch (e) {
                // Ignoring parse error for partial lines if any
                console.log('RAW:', line);
            }
        }
    }
    // Keep the last part in buffer
    buffer = lines[lines.length - 1];
});

server.stderr.on('data', (data) => {
    console.error('STDERR:', data.toString());
});

// Initialize
server.stdin.write(JSON.stringify({
    jsonrpc: '2.0',
    method: 'initialize',
    params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test-client', version: '1.0.0' }
    },
    id: 1
}) + '\n');

// Wait, then call the tool
setTimeout(() => {
    console.log('Sending tools/call request...');
    server.stdin.write(JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
            name: 'task',
            arguments: {
                task: 'List the files in the current directory. Output only the file list, no explanation.',
                cwd: process.cwd()
            }
        },
        id: 2
    }) + '\n');
}, 2000);

// Timeout and cleanup (extended because Claude Code might take time to init and run)
setTimeout(() => {
    server.kill();
    process.exit(0);
}, 60000);
