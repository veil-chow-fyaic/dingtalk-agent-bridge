import { dirname, join } from "node:path";
import { loadOutboundMediaFromUrl } from "openclaw/plugin-sdk/outbound-media";
import { extractOriginalFilename, getMediaDir } from "openclaw/plugin-sdk/media-runtime";
import { createChannel, ID } from "./channel.mjs";

const outboundRoot = () => join(getMediaDir(), "outbound");
async function loadMedia(path, options) {
  const original = await loadOutboundMediaFromUrl(path, options);
  if (dirname(path) === outboundRoot()) {
    return {...original, fileName:extractOriginalFilename(path)};
  }
  return original;
}
export default {
  id:ID, name:"DingTalk Bridge",
  register(api) {
    api.registerChannel({plugin:createChannel({loadMedia,replyMediaRoots:()=>[outboundRoot()]})});
  },
};
