import { dirname, join } from "node:path";
import { loadWebMediaRaw } from "openclaw/plugin-sdk/web-media";
import { buildOutboundMediaLoadOptions, extractOriginalFilename, getMediaDir } from "openclaw/plugin-sdk/media-runtime";
import { buildAgentSessionKey, resolveAgentRoute } from "openclaw/plugin-sdk/routing";
import { createChannel, ID, supportsHostVersion } from "./channel.mjs";

const outboundRoot = () => join(getMediaDir(), "outbound");
async function loadMedia(path, options) {
  // The July convenience loader optimizes images. Preserve original bytes within the host media policy.
  const original = await loadWebMediaRaw(path, buildOutboundMediaLoadOptions(options));
  if (dirname(path) === outboundRoot()) {
    return {...original, fileName:extractOriginalFilename(path)};
  }
  return original;
}
export default {
  id:ID, name:"DingTalk Bridge",
  register(api) {
    if (!supportsHostVersion(api.runtime.version)) {
      throw new Error("DingTalk Bridge supports OpenClaw 2026.7.1-2 or stable >=2026.11.3 <2027");
    }
    api.registerChannel({plugin:createChannel({loadMedia,replyMediaRoots:()=>[outboundRoot()],
      routing:{buildAgentSessionKey,resolveAgentRoute}})});
  },
};
