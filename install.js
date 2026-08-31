const { spawnSync } = require('child_process');

const url = 'https://raw.githubusercontent.com/DaniellRG/IAinvicible/main/install.ps1';
const cmd = "[Net.ServicePointManager]::SecurityProtocol = 3072; iex (irm '" + url + "')";

console.log('Installing IA Invisible...');
console.log('This can take a few minutes. Do not close this window.');

const r = spawnSync('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', cmd], {
    stdio: 'inherit',
    windowsHide: true
});

if (r.status !== 0) {
    console.error('IA Invisible installation failed. Check your internet connection.');
    process.exit(r.status || 1);
}