const { spawn } = require('child_process');

const server = spawn('npx', ['claude-code-mcp'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true
});

server.stdout.on('data', (data) => {
    console.log(data.toString());
});

server.stderr.on('data', (data) => {
    console.error('STDERR:', data.toString());
});

const init = {
    jsonrpc: '2.0',
    method: 'initialize',
    params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test-client', version: '1.0.0' }
    },
    id: 1
};

server.stdin.write(JSON.stringify(init) + '\n');

setTimeout(() => {
    const listTools = {
        jsonrpc: '2.0',
        method: 'tools/list',
        params: {},
        id: 2
    };
    server.stdin.write(JSON.stringify(listTools) + '\n');
}, 2000);

setTimeout(() => {
    server.kill();
    process.exit(0);
}, 5000);
