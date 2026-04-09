export function onRequest(context) {
  return Response.json({ ok: true, env_keys: Object.keys(context.env) })
}
