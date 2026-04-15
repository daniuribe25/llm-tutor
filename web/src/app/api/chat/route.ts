import { getBackendUrl } from "@/lib/backend-url";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const backend = getBackendUrl();
  const body = await request.json();

  const upstream = await fetch(`${backend}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    return new Response(
      JSON.stringify({ error: `Backend error: ${upstream.status}` }),
      { status: upstream.status, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
