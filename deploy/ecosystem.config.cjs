// PM2 process file for the storefront (same VPS as ERPNext).
// Usage (from the storefront folder):  pm2 start ../deploy/ecosystem.config.cjs && pm2 save
// instances stays at 1 (fork mode) unless REDIS_URL is set: without Redis the first rate-limit
// layer counts per process, so several instances would each allow the full limit.
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
