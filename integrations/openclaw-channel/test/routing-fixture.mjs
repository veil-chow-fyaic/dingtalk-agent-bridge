// Small routing seam for transport tests; the versioned SDK contract suite uses the real implementation.
export function buildAgentSessionKey({agentId,channel,accountId,peer}) {
  return ["agent",agentId,channel,...(peer.kind==="direct"?[accountId]:[]),peer.kind,peer.id].join(":");
}
export const routing = {buildAgentSessionKey,resolveAgentRoute(params) {
  return {agentId:"agent",sessionKey:buildAgentSessionKey({...params,agentId:"agent"}),mainSessionKey:"agent:agent:main"};
}};
