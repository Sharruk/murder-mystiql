const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const https = require("https");

const pkgs = [
  "typescript@5.6.3",
  "vite@5.4.11",
  "@vitejs/plugin-react@4.3.4",
  "react@18.3.1",
  "react-dom@18.3.1",
  "lucide-react@0.468.0",
  "firebase@10.14.1",
  "@types/react@18.3.18",
  "@types/react-dom@18.3.5",
  "esbuild@0.21.5",
  "rollup@4.24.0",
  "picocolors@1.1.1",
  "source-map-js@1.2.1",
  "postcss@8.4.49",
  "nanoid@3.3.8",
  "@esbuild/win32-x64@0.21.5",
  "@rollup/rollup-win32-x64-msvc@4.24.0",
];

async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { "User-Agent": "node" } }, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => resolve(JSON.parse(data)));
      res.on("error", reject);
    });
  });
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, { headers: { "User-Agent": "node" } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return downloadFile(res.headers.location, dest).then(resolve).catch(reject);
      }
      res.pipe(file);
      file.on("finish", () => {
        file.close();
        resolve();
      });
      file.on("error", reject);
    });
  });
}

async function install() {
  const tmpDir = path.join(__dirname, "../node_modules/.tmp_tar");
  fs.mkdirSync(tmpDir, { recursive: true });

  for (const pkg of pkgs) {
    const [name, version] = pkg.startsWith("@")
      ? ["@" + pkg.slice(1).split("@")[0], pkg.slice(1).split("@")[1]]
      : pkg.split("@");
    const targetDir = path.join(__dirname, "../node_modules", name);
    if (fs.existsSync(path.join(targetDir, "package.json"))) {
      console.log(`Already installed ${name}`);
      continue;
    }

    const tarFile = path.join(tmpDir, `${name.replace(/\//g, "-")}-${version}.tgz`);
    if (!fs.existsSync(tarFile) || fs.statSync(tarFile).size === 0) {
      console.log(`Resolving ${name}@${version}...`);
      try {
        const info = await fetchJson(`https://registry.npmjs.org/${encodeURIComponent(name)}/${version}`);
        console.log(`Downloading ${name}...`);
        await downloadFile(info.dist.tarball, tarFile);
      } catch (e) {
        console.error(`Download failed ${name}:`, e.message);
        continue;
      }
    }

    try {
      fs.mkdirSync(targetDir, { recursive: true });
      execSync(`tar -xzf "${tarFile}" --strip-components=1 -C "${targetDir}"`, { stdio: "inherit" });
      console.log(`Extracted ${name}`);
    } catch (e) {
      console.error(`Extract failed ${name}:`, e.message);
    }
  }

  const binDir = path.join(__dirname, "../node_modules/.bin");
  fs.mkdirSync(binDir, { recursive: true });
  fs.writeFileSync(
    path.join(binDir, "tsc.cmd"),
    `@echo off\nnode "%~dp0/../typescript/bin/tsc" %*\n`
  );
  fs.writeFileSync(
    path.join(binDir, "vite.cmd"),
    `@echo off\nnode "%~dp0/../vite/bin/vite.js" %*\n`
  );
  console.log("Setup completed successfully!");
}

install();
