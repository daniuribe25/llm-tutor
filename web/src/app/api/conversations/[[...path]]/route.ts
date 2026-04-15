import type { NextRequest } from "next/server";

import { getBackendUrl } from "@/lib/backend-url";

export const dynamic = "force-dynamic";

function upstreamUrl(req: NextRequest, segments: string[] | undefined): string {
  const base = getBackendUrl();
  const tail = segments?.length ? `/${segments.join("/")}` : "";
  return `${base}/api/conversations${tail}${req.nextUrl.search}`;
}

async function proxy(req: NextRequest, segments: string[] | undefined) {
  const url = upstreamUrl(req, segments);
  const init: RequestInit = {
    method: req.method,
    cache: "no-store",
    headers: {},
  };

  const contentType = req.headers.get("Content-Type");
  if (contentType) {
    (init.headers as Record<string, string>)["Content-Type"] = contentType;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(url, init);

  const resHeaders = new Headers();
  const ct = upstream.headers.get("Content-Type");
  if (ct) resHeaders.set("Content-Type", ct);

  return new Response(upstream.body, {
    status: upstream.status,
    headers: resHeaders,
  });
}

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
