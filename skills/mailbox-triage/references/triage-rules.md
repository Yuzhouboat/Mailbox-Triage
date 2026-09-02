# Mailbox Triage Rules

Use these defaults unless the user overrides them in the thread.

Classify each message into exactly one group. Use the headings below. If a message
fits none of them, assign it to the `Uncategorized` group (defined at the end).

## Group Mapping

Use these exact headings as the grouping taxonomy for catch-up summaries and grouped email reports.

### P1 - Urgent

- named deadlines requiring same-day or next-day response
- requests with clear and immediate business impact
- issues that will escalate or cause damage if not handled quickly
- complaints or notices that require fast action to prevent further consequences
- messages from accounts or people the user has flagged as high-priority

### P2 - Actionable

- active project emails tied to topics the user is tracking
- requests that need a response but are not immediately urgent
- notices that require follow-up work or a decision
- reports or updates that imply a next step from the user

### P3 - Monitor

- status updates and confirmations worth awareness but no action needed now
- routine reports that show everything is working normally
- informational notices that may become relevant later

### P4 - Low Signal

- newsletters and promotional emails
- out-of-office replies not connected to an active thread
- automated digests or reports that show no anomalies
- verification or notification emails not tied to active work

### Uncategorized

- the default fallback group for any message that does not clearly fit a group above
- use this instead of forcing a message into a poorly matching group

## Output Preferences

- Use the exact group headings above when the user asks for grouped summaries.
- List the `Uncategorized` group last so unmatched messages are easy to scan and reclassify.
- Within each priority heading, consolidate repeated or closely related messages that share the same root cause, sender pattern, or topic. Do not consolidate unrelated messages merely because they share a P1/P2/P3/P4 heading.
- For each cluster, select one representative message, preferring the clearest subject and most informative body. Show only its sender and verbatim `Subject:`, append the total similar-message count as `(xN)`, and omit all other emails and subjects in that cluster. For a single-message item, show its sender and verbatim subject without a count.
- Write a one-to-two sentence plain-English summary for each item.
- Mark items that need a follow-up action with `[Follow-up needed]`.
- Mark items that are high-priority or time-sensitive with `[Priority]` based on business impact (suppression risk, named deadlines, revenue impact, key stakeholder requests) — not just urgency words.
- Use sender, subject, timestamp, and durable identifiers (EWS item ID or message ID) internally for deduplication and filing. In the user-facing report and saved draft, identify messages only by sender and exact subject; never include timestamps, message identifiers, mailbox URLs, or links.
- When the root cause is in an attachment, keep classification provisional until the attachment is inspected.
