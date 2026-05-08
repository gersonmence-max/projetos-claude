import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@smb-os/ui", "@smb-os/utils", "@smb-os/types"],
};

export default nextConfig;
