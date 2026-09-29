# Mailbox Triage Rules

Default groups. To customize, copy this file to `config/triage-rules.md` in the skill directory (gitignored) and edit it; the report format lives in SKILL.md.

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
