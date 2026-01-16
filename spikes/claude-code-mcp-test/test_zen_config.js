const { spawn } = require('child_process');

const server = spawn('npx', ['claude-code-mcp'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true
});

let buffer = '';

server.stdout.on('data', (data) => {
    buffer += data.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line

    for (const line of lines) {
        if (line.trim()) {
            try {
                const msg = JSON.parse(line);
                console.log('RESPONSE:', JSON.stringify(msg, null, 2));
            } catch (e) {
                console.log('RAW STDOUT:', line);
            }
        }
    }
});

server.stderr.on('data', (data) => {
    console.error('STDERR:', data.toString());
});

server.on('close', (code) => {
    console.log(`Child process exited with code ${code}`);
});

// Initialize
const initMsg = {
    jsonrpc: '2.0',
    method: 'initialize',
    params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test-client', version: '1.0.0' }
    },
    id: 1
};
console.log('Sending Initialize...');
server.stdin.write(JSON.stringify(initMsg) + '\n');

// Call 1: List Files
setTimeout(() => {
    console.log('Sending Call 1 (List Files)...');
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
}, 3000);

// Call 2: Structured Output
setTimeout(() => {
    console.log('Sending Call 2 (Structured Output)...');
    server.stdin.write(JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
            name: 'task',
            arguments: {
                task: `Analyze the current directory and produce a YAML report with this exact schema:
---
analysis_type: directory_scan
timestamp: <ISO8601>
file_count: <integer>
status: success
files:
  - name: <filename>
    type: file
Output ONLY the YAML.`,
                cwd: process.cwd()
            }
        },
        id: 3
    }) + '\n');
}, 15000);

// Exit
setTimeout(() => {
    console.log('Test complete, killing server...');
    server.kill();
    process.exit(0);
}, 45000);
