# Chatbase-Assisted LinkedIn Draft Approval Workflow

Author: **Abu Ali**

## Purpose

This project uses Chatbase as a **review and guidance assistant**, not as the final publishing authority. The safest ownership model is to let the automation generate LinkedIn drafts, let Chatbase help the owner evaluate and improve the draft, and then require the owner to manually trigger publication through GitHub Actions.

> **Recommended rule:** Chatbase may advise, score, rewrite, and explain a draft, but only the repository owner should approve the final publish action.

## Recommended Operating Model

The workflow is **draft-first**. Scheduled automation generates a draft JSON file and updates the dashboard. The owner then opens Chatbase, pastes the draft, asks for a quality review, applies improvements if needed, and finally runs the manual GitHub workflow action to publish the selected draft path.

| Step | Actor | Action | Output |
|---|---|---|---|
| 1 | GitHub Actions | Generate a draft on the normal schedule | `posts_history/YYYY-MM-DD-*.json` with `status=draft` |
| 2 | Dashboard | Display the draft as **Needs review** | Owner sees what requires attention |
| 3 | Chatbase | Review the draft against the brand checklist | Recommendations, risks, revised version |
| 4 | Owner | Decide whether the draft is good enough | Approved or rejected decision |
| 5 | GitHub Actions | Publish only when manually triggered | LinkedIn post and archived status update |

## Why This Is the Best Design

The project represents a personal LinkedIn brand, so publishing should never be fully delegated to an external chatbot. A human approval gate protects reputation, prevents repetitive or inaccurate posts, and ensures the final message still sounds like the owner. Chatbase is valuable because it can make the review process faster and more consistent, but it should not bypass the owner.

## Chatbase Review Prompt

Use this prompt inside Chatbase when reviewing a generated draft:

```text
You are reviewing a LinkedIn post draft for Abu Ali's professional personal brand.

Evaluate the draft using this checklist:
1. Is the opening hook strong enough for LinkedIn?
2. Does the post sound human, practical, and non-generic?
3. Is the message aligned with leadership, AI/tech, marketing, or business growth?
4. Is there any risky, exaggerated, inaccurate, or overly promotional claim?
5. Is the post clear, concise, and suitable for senior professional readers?
6. Does it end with a meaningful question or call to conversation?
7. Should this draft be approved, revised, or rejected?

Return:
- Approval decision: Approve / Revise / Reject
- Quality score from 1 to 10
- Main risks
- Suggested improved version
- Final publishing recommendation

Draft:
[PASTE DRAFT HERE]
```

## How to Publish an Approved Draft

After Chatbase approves a draft (or you decide it is ready), publish it through GitHub Actions:

1. Go to **Actions → Auto-post to LinkedIn → Run workflow**
2. Set **action** = `publish_draft`
3. Set **draft_file** = the JSON path shown on the dashboard, e.g. `posts_history/20260430_090000_ai.json`
4. Click **Run workflow**

The workflow will mark the draft as published and update the dashboard.

## Future Automation Option

If a Chatbase API or a Make scenario is available later, the project can send each draft automatically to Chatbase for review. The output should be saved back into the draft JSON as review metadata.

| Future Field | Meaning |
|---|---|
| `chatbase_reviewed` | Whether the draft has passed through the assistant review step |
| `chatbase_score` | Suggested quality score from 1 to 10 |
| `chatbase_recommendation` | `approve`, `revise`, or `reject` |
| `chatbase_notes` | Human-readable review comments |
| `owner_approved` | Final owner approval before publishing |

Even with API automation, publishing should still require manual confirmation.

## Owner Policy

A draft should only be published when it meets all of the following conditions: it is accurate, it matches the owner's voice, it adds a real insight, it does not repeat recent posts, and it has been deliberately approved by the owner.
