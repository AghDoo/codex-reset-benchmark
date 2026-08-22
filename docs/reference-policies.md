# Collection, Correction, and Opt-out Policy

## Responsible collection

Collectors run at most once per hour per enabled source in the default workflow. They use a descriptive User-Agent, bounded response size, timeout, and standard HTTP retrieval.

The project does not:

- authenticate to forecast sites;
- send private cookies or credentials;
- bypass CAPTCHA, Cloudflare/anti-bot challenges, paywalls, login gates, or explicit rate limits;
- retry aggressively after 401, 403, or 429 responses;
- store full copies of third-party pages.

Where a source publishes `robots.txt`, the collector checks it before collection. A denied path is skipped. A source can be disabled if its operator asks not to be collected.

## Ground Truth freshness

Ground Truth requires human review because reset-like announcements must be classified against the benchmark methodology. An independent watchdog runs every six hours and treats `data/events/resets.json` as operationally stale when its top-level `reviewed_at` is more than 36 hours old.

The 36-hour threshold is an operational maintenance target, not a scoring rule. When the threshold is exceeded, the watchdog opens one fixed GitHub alert issue. Repeated checks reuse the same open alert instead of creating duplicates. After `reviewed_at` is advanced and becomes fresh again, the watchdog closes the alert automatically.

Scoring continues to use `reviewed_at` itself as the resolution boundary, so stale Ground Truth never causes unreviewed time to be silently scored as a negative outcome.

## Attribution

Every snapshot records the source ID and source URL. The website links to source sites by name and does not reuse their logos or visual identity.

## Corrections

Forecast history is append-only. If a collector bug archives an incorrect value, do not edit the original NDJSON line. Record a correction/supersession in a later schema revision and exclude the bad snapshot through an explicit correction rule.

Ground-truth corrections similarly preserve the original decision or event identifier and document the reason for supersession.

## Source opt-out

A site operator can open a repository issue requesting collection changes or opt-out. Maintainers should disable the source while a credible request is reviewed.

## Legal note

This policy is an engineering and research practice, not legal advice. Contributors are responsible for respecting applicable law and source-specific terms.
