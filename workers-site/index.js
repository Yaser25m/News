import { getAssetFromKV } from '@cloudflare/kv-asset-handler'

/**
 * The DEBUG flag will do two things:
 * 1. We will skip caching on the edge, which makes it easier to debug
 * 2. We will return an error message on exception in your Response rather than the default 404.html page
 */
const DEBUG = true

addEventListener('fetch', event => {
  try {
    event.respondWith(handleEvent(event))
  } catch (e) {
    if (DEBUG) {
      return event.respondWith(
        new Response(e.message || e.toString(), {
          status: 500,
        }),
      )
    }
    event.respondWith(new Response('Internal Error', { status: 500 }))
  }
})

async function handleEvent(event) {
  const url = new URL(event.request.url)
  let options = {}

  // Always serve index.html for the root path
  if (url.pathname === '/') {
    options.mapRequestToAsset = req => new Request(`${new URL(req.url).origin}/index.html`, req)
  }

  try {
    if (DEBUG) {
      options.cacheControl = {
        bypassCache: true,
      }
    }

    // Try to get the asset from KV
    const response = await getAssetFromKV(event, options)

    // Add appropriate headers
    const headers = new Headers(response.headers)
    headers.set('Content-Type', 'text/html; charset=UTF-8')

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers
    })
  } catch (e) {
    console.error(`Error: ${e.message}`)

    // if an error is thrown try to serve the asset at 404.html
    try {
      let notFoundResponse = await getAssetFromKV(event, {
        mapRequestToAsset: req => new Request(`${new URL(req.url).origin}/404.html`, req),
      })

      return new Response(notFoundResponse.body, {
        ...notFoundResponse,
        status: 404,
      })
    } catch (e) {
      console.error(`Error serving 404: ${e.message}`)

      // If we can't serve the 404 page, serve a simple error message
      return new Response('Page not found', {
        status: 404,
        headers: {
          'Content-Type': 'text/html; charset=UTF-8'
        }
      })
    }
  }
}
