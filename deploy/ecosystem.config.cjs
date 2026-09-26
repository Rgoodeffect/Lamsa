// PM2 process file for the storefront (same VPS as ERPNext).
// Usage (from the storefront folder):  pm2 start ../deploy/ecosystem.config.cjs && pm2 save
// Keep instances at 1 (fork mode): the first rate-limit layer is in-memory per process.
module.exports = {
  apps: [
    {
      name: "lamsa-storefront",
      cwd: __dirname + "/../storefront",
      script: "node_modules/next/dist/bin/next",
      args: "start -p 3000 -H 127.0.0.1",
      instances: 1,
      exec_mode: "fork",
      max_memory_restart: "700M",
      env: { NODE_ENV: "production" },
    },
  ],
};
