const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const local = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
const appDir = path.join(local, 'IAInvisible');
const mainPy = path.join(appDir, 'main.py');

const candidates = [
    path.join(appDir, 'python_embed', 'pythonw.exe'),
    path.join(appDir, 'python_embed', 'python.exe'),
    path.join(local, 'Programs', 'Python', 'Python314', 'pythonw.exe'),
    path.join(local, 'Programs', 'Python', 'Python313', 'pythonw.exe'),
    path.join(local, 'Programs', 'Python', 'Python312', 'pythonw.exe'),
    'C:\\Python314\\pythonw.exe',
    'C:\\Python313\\pythonw.exe',
    'C:\\Python312\\pythonw.exe'
];

const py = candidates.find(function (c) { return fs.existsSync(c); });

if (!py) {
    console.error('IA Invisible: Python not found. Re-run the install command.');
    process.exit(1);
}

const child = spawn(py, [mainPy], { detached: true, stdio: 'ignore', cwd: appDir });
child.unref();
setTimeout(function () { process.exit(0); }, 100);