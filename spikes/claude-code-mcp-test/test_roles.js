const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Configuration
const MOCK_REPO = path.join(process.cwd(), 'mock_repo');
const REFACTOR_PLAN = path.join(MOCK_REPO, 'REFACTOR_PLAN.md');

async function runAgent(role, prompt, files = []) {
    return new Promise((resolve, reject) => {
        console.log(`\n[${role}] Starting agent...`);

        // Spawn server process
        const server = spawn('npx', ['claude-code-mcp'], {
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: true
        });

        let buffer = '';
        let responseText = '';
        let serverKilled = false;

        // Handle stdio
        server.stdout.on('data', (data) => {
            buffer += data.toString();
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const msg = JSON.parse(line);
                        if (msg.method === 'notifications/message') {
                            const data = JSON.parse(msg.params.data);
                            // Log agent output
                            if (data.type === 'assistant' && data.message && Arr) {
                                // Streaming content... this is complex to parse live, 
                                // just log it or capture it?
                            }
                            // Check for result
                            if (data.type === 'result' && !data.is_error) {
                                console.log(`[${role}] SUCCESS:`, data.result);
                                responseText = data.result;
                                if (!serverKilled) { server.kill(); serverKilled = true; resolve(responseText); }
                            }
                            if (data.type === 'result' && data.is_error) {
                                console.log(`[${role}] ERROR:`, data.error);
                                if (!serverKilled) { server.kill(); serverKilled = true; reject(data.error); }
                            }
                        }
                    } catch (e) { }
                }
            }
        });

        // Setup Init
        const initMsg = {
            jsonrpc: '2.0',
            method: 'initialize',
            params: {
                protocolVersion: '2024-11-05',
                capabilities: {},
                clientInfo: { name: 'test-driver', version: '1.0.0' }
            },
            id: 1
        };
        server.stdin.write(JSON.stringify(initMsg) + '\n');

        // Send Prompt
        setTimeout(() => {
            console.log(`[${role}] Sending prompt...`);
            server.stdin.write(JSON.stringify({
                jsonrpc: '2.0',
                method: 'tools/call',
                params: {
                    name: 'task',
                    arguments: {
                        task: prompt,
                        cwd: MOCK_REPO
                    }
                },
                id: 2
            }) + '\n');
        }, 2000); // 2s warmup

        // Timeout
        setTimeout(() => {
            if (!serverKilled) {
                console.log(`[${role}] TIMEOUT.`);
                server.kill();
                reject('TIMEOUT');
            }
        }, 90000); // 90s timeout (GLM might be slow)
    });
}

async function main() {
    try {
        // --- PHASE 1: ARCHITECT ---
        console.log('=== PHASE 1: ARCHITECT ===');
        const architectPrompt = `You are a Senior Architect. Analyze the current directory. 
        I want to refactor 'utils.py' by splitting it into 'string_utils.py' and 'math_utils.py'.
        Create a file named 'REFACTOR_PLAN.md' that lists:
        1. Which functions move to string_utils.py
        2. Which functions move to math_utils.py
        3. A summary of the plan.
        DO NOT execute the refactor. ONLY create the plan file.`;

        await runAgent('Architect', architectPrompt);

        // Verify Plan exists
        if (fs.existsSync(REFACTOR_PLAN)) {
            console.log('\n[Driver] Plan created successfully:');
            console.log(fs.readFileSync(REFACTOR_PLAN, 'utf8'));
        } else {
            throw new Error('Architect failed to create REFACTOR_PLAN.md');
        }

        // --- PHASE 2: BUILDER ---
        console.log('\n=== PHASE 2: BUILDER ===');
        const builderPrompt = `You are a Builder. Read 'REFACTOR_PLAN.md'.
        Execute the plan:
        1. Create the new files with the correct code from utils.py.
        2. Update main.py to import from the new modules.
        3. Delete utils.py.
        4. Run 'python main.py' to verify it works.`;

        await runAgent('Builder', builderPrompt);

        // Verify Outcome
        if (!fs.existsSync(path.join(MOCK_REPO, 'utils.py'))) {
            console.log('[Driver] utils.py deleted [PASS]');
        } else {
            console.log('[Driver] utils.py still exists [FAIL]');
        }

        if (fs.existsSync(path.join(MOCK_REPO, 'string_utils.py'))) {
            console.log('[Driver] string_utils.py created [PASS]');
        }

    } catch (e) {
        console.error('\n[Driver] FAILED:', e);
        process.exit(1);
    }
}

main();
