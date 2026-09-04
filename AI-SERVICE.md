# In-app AI research

The Windows and Linux dashboard now has **Ask AI for help**. Review and edit the exact summary, optionally include a redacted evidence excerpt, then press **Send this summary & ask AI**. Results and clickable citations appear in the dashboard. No file sharing or ChatGPT conversation is required. Closing the review without sending makes no research request.

This source implementation is not a deployed service. No live provider call has been tested. The app shows an honest disconnected state until the operator configures it.

## Operator setup

Run `research_service.py` with Python 3.11+ on a server. It uses the standard library and listens only on `127.0.0.1:8787`. Put an HTTPS reverse proxy in front of it, routing only `/research`. Set a proxy request body limit of 50 KB, a read timeout above 90 seconds, connection/rate limits, and disable request-body and authorization-header logging. Do not expose Python's development HTTP server directly to the internet.

Supply these through the host's secret manager or protected environment, never source control or the installer:

- `OPENAI_API_KEY`: operator's project API key with billing configured.
- `LANTERN_CLIENT_TOKEN_SHA256`: comma-separated SHA-256 hashes of independent random installation tokens. Generate each token using `secrets.token_urlsafe(32)` and hash its UTF-8 bytes with SHA-256. Provision the original token securely to its installation. Removing its hash revokes access after a service restart.
- `LANTERN_RESEARCH_MODEL`: optional; defaults to `gpt-5.4-mini`.

Start with `python research_service.py`. Configure each desktop's launch environment:

- `LANTERN_RESEARCH_URL=https://YOUR-SERVICE/research`
- `LANTERN_RESEARCH_TOKEN`: that installation's token, not the OpenAI key.

Restart Lantern after configuring these. This MVP needs operator provisioning; account sign-in, automatic enrollment and a hosted subscription service are not implemented. End users use the same research buttons on both operating systems once provisioned.

## Privacy, costs and limitations

Only the reviewed text is transmitted by the desktop. Default drafts omit raw evidence. Redaction is best effort: review names, addresses and private details before sending. The service sends the summary to OpenAI; searches may contain details derived from it. The operator and OpenAI process the request. `store: false` disables Responses application-state storage; it is not a promise of zero provider retention. Read [OpenAI's data controls](https://developers.openai.com/api/docs/guides/your-data).

The service does not intentionally write summaries or answers to disk. Hosting/proxy monitoring must also be configured appropriately. Results remain in desktop session memory and can appear in a user-requested full report export. Research uses a paid API, not a ChatGPT subscription.

There is one active desktop request, a 30-second submission cooldown, four concurrent gateway requests, and 20 requests per installation per UTC day. Gateway quotas are memory-only and reset on restart; deploy durable quotas, user accounts and operator billing controls before public release. Requests are not automatically retried. A timeout can still incur a charge. Closing the app does not cancel provider work already submitted.

AI responses are advisory text with citations. They have no connection to the repair helper, command execution or the repair allowlist. AI can be mistaken; it cannot manufacture a new automatic repair. Existing vetted fixes still use their own review, elevation and backup workflow.

Implementation uses the [Responses API web search tool](https://developers.openai.com/api/docs/guides/tools-web-search). Tests mock network responses; actual HTTPS deployment, authentication, billing and live research require an operator acceptance check before distribution.
