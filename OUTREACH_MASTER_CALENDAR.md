# SmartPRO Hub — Complete Outreach Sequence Calendar
*All scripts ready to paste. After each session, advance prospects in terminal.*

---

## ✅ MAY 28 — DAY 1 (DONE)
All 20: Like + comment → `TODAY_OUTREACH_DAY1.md`

---

## MAY 30 — Segment C: Connection Requests
**2 people · 5 minutes**

- **OA-018 Omar Al-Ismaili** → Connect (NO note)
- **OA-019 Layla Al-Nabhani** → Connect (NO note)

```python
python -c "from outreach_tracker import advance_prospect; [advance_prospect(i) for i in ['OA-018','OA-019']]"
```

---

## MAY 31 — Segment A: Share Their Post
**14 people · 45 minutes · scripts in `OUTREACH_MAY31_DAY4_SEG_A.md`**

After completing:
```python
python -c "
from outreach_tracker import advance_prospect
ids = ['OA-002','OA-003','OA-004','OA-005','OA-006','OA-007','OA-008',
       'OA-009','OA-010','OA-011','OA-012','OA-013','OA-014','OA-020']
[advance_prospect(i) for i in ids]
print('Done')
"
```

---

## JUNE 1 — Segment B: Connection Requests + Segment C: DMs

### Segment B — Personalized connection request notes (3 people · 10 min)

**OA-015 · Tariq Al-Busaidi — Busaidi Family Office**
Connect → Add note:
> Tariq, I'm building Oman's first multi-tenant HR and Sanad compliance platform — 924 licensed offices, all still on Excel. Thought it worth connecting given your focus on local SaaS opportunities.

---

**OA-016 · Reem Al-Mahrouqi — Oman Technology Fund**
Connect → Add note:
> Reem, building SmartPRO Hub — HR, payroll, and Ministry of Labour compliance for Oman SMEs. First-mover in a market being pushed forward by Vision 2040 enforcement. Would value connecting with someone tracking this space.

---

**OA-017 · Zaid Al-Amri — GCC SaaS Ventures**
Connect → Add note:
> Zaid, I'm building SmartPRO Hub — Oman-native HR compliance SaaS with a clear GCC expansion path. You've invested in govtech and HR tech across the region. Think there's a conversation worth having.

---

### Segment C — First DMs (2 people · 10 min)

**OA-018 · Omar Al-Ismaili — Ismaili Tech Ventures**
DM (after connection accepted):
> Omar, appreciate the connection. Saw your post on multi-tenant architecture — we're solving a similar problem on the compliance layer for GCC labour law. Each jurisdiction has different data residency and audit trail requirements, so it has to be schema-deep, not a bolt-on. Building SmartPRO Hub for Oman first. Would be curious to compare notes on how you're handling tenant isolation if you're open to it — no agenda, just a technical conversation.

---

**OA-019 · Layla Al-Nabhani — Nabhani Digital**
DM (after connection accepted):
> Layla, good to connect. Building SmartPRO Hub — HR and compliance platform built natively for Oman rather than adapted from a Western tool. You're building digital products for the local market too, so I imagine you've run into the same problem: user assumptions baked into global SaaS that just don't fit here. If there's any overlap in what we're building that's worth a conversation — whether that's partnership, integration, or just comparing notes — happy to find 20 minutes.

---

```python
python -c "from outreach_tracker import advance_prospect; [advance_prospect(i) for i in ['OA-015','OA-016','OA-017','OA-018','OA-019']]"
```

---

## JUNE 3 — Segment A: Connection Requests + OA-001 (15 people · 20 min)

**Action: Connect — NO note for any of them.**
The like, comment, and share have already done the priming. A note now looks like you're pitching.

Connect with (in order):
- OA-001 Ahmed Al-Balushi *(ahead of others — also connects today)*
- OA-002 Khalid Al-Rashdi
- OA-003 Fatma Al-Hinai
- OA-004 Mohammed Al-Mamari
- OA-005 Salim Al-Habsi
- OA-006 Sara Al-Lawati
- OA-007 Hamad Al-Siyabi
- OA-008 Nadia Al-Tobi
- OA-009 Yusuf Al-Kindi
- OA-010 Mariam Al-Zadjali
- OA-011 Ibrahim Al-Rawahi
- OA-012 Ali Al-Ghafri
- OA-013 Bader Al-Maqbali
- OA-014 Huda Al-Barwani
- OA-020 Faisal Al-Hosni

```python
python -c "
from outreach_tracker import advance_prospect
ids = ['OA-001','OA-002','OA-003','OA-004','OA-005','OA-006','OA-007',
       'OA-008','OA-009','OA-010','OA-011','OA-012','OA-013','OA-014','OA-020']
[advance_prospect(i) for i in ids]
print('Done')
"
```

---

## JUNE 4 — Segment B: DMs with PDF (3 people · 15 min)

Attach `SmartPROHub_Overview.pdf` to each DM.

**OA-015 · Tariq Al-Busaidi — Busaidi Family Office**
> Tariq, thanks for connecting. Attaching a one-page overview of SmartPRO Hub — Oman's first multi-tenant HR and Sanad compliance platform. The market context is on page 1: 924 licensed Sanad offices, ~15,000 Oman SMEs with 10–200 employees, all currently running compliance on Excel and WhatsApp. Vision 2040 enforcement is accelerating the need. We're live with paying customers. Happy to walk you through the numbers on a 20-minute call if this fits your current focus.

---

**OA-016 · Reem Al-Mahrouqi — Oman Technology Fund**
> Reem, appreciate the connection. Attaching a one-pager on SmartPRO Hub. We're at an early stage where a conversation with someone tracking Oman's digital infrastructure space would be genuinely useful — not to pitch, but to get a sharper view of where you see the ecosystem going. The market section on page 1 gives the context. If a 20-minute call makes sense, I'll keep it tight and specific.

---

**OA-017 · Zaid Al-Amri — GCC SaaS Ventures**
> Zaid, thanks for connecting. Attaching the SmartPRO Hub one-pager. The Oman-first, GCC-expansion thesis is on page 1. Short version: Oman's regulatory structure is distinct enough that native-built solutions have a defensibility advantage, but the operational patterns transfer cleanly to Bahrain and Kuwait. We're live, we have paying customers, and we're at the stage where the right early conversations matter. If this fits anything you're looking at, a 20-minute call works on my end.

---

```python
python -c "from outreach_tracker import advance_prospect; [advance_prospect(i) for i in ['OA-015','OA-016','OA-017']]"
```

---

## JUNE 5 — Segment A: First Direct Messages (14 people · 60 min)

**Wait until connection is accepted before sending.** If not yet accepted, skip and come back in 2 days.

---

**OA-002 · Khalid Al-Rashdi *(Arabic)***
> خالد، شكراً للتواصل. لاحظت من منشوراتك أنك تدير تقديم ملفات وزارة العمل لأكثر من ١٥ شركة — هذا بالضبط ما بنيت SmartPRO Hub من أجله. نظام واحد يتتبع المواعيد النهائية لكل عميل، يُرسل التنبيهات تلقائياً، ويُصدر الفواتير عند إغلاق كل ملف. لو كان لديك ١٥ دقيقة لنرى إن كان يحل مشكلة حقيقية عندك، أخبرني.

*(Khalid, thanks for connecting. I noticed from your posts that you manage Ministry of Labour filings for 15+ companies — that's exactly what I built SmartPRO Hub for. One system tracks every client's deadlines, fires alerts automatically, and invoices when each case closes. If you have 15 minutes to see whether it solves a real problem for you, let me know.)*

---

**OA-003 · Fatma Al-Hinai *(English)***
> Fatma, thanks for connecting. You mentioned WPS takes 2+ days every month for your team — that's the problem we built SmartPRO Hub to eliminate. We handle the full WPS cycle: employee record validation, bank-specific formatting, pre-submission error checking, and direct submission. A company similar to yours went from 2+ days to 23 minutes. Happy to show you exactly how in a 20-minute demo — no commitment, no sales deck, just the product running against a real payroll scenario. Interested?

---

**OA-004 · Mohammed Al-Mamari *(English)***
> Mohammed, good to connect. Running HR admin for 30–80 employees as a CEO is a real drain — that Monday morning time shouldn't be yours. SmartPRO Hub is built for owners who want HR to run without them at the centre. We handle payroll, WPS, leave, and Ministry filings in one place. If 3 hours on a Monday sounds familiar, I'd be glad to show you what the alternative looks like. 20 minutes, your call.

---

**OA-005 · Salim Al-Habsi *(Arabic)***
> سالم، شكراً للتواصل. إدارة ١٠–١٥ عميلاً بدون تنبيهات تلقائية لانتهاء الصلاحيات هي مشكلة حقيقية — اكتشاف تصريح منتهي من العميل نفسه هو أسوأ سيناريو. SmartPRO Hub يُرسل تنبيهات قبل ٣٠ و٧ أيام لكل تصريح لكل عميل. لو تريد ترى كيف يعمل، ١٥ دقيقة تكفي.

*(Salim, thanks for connecting. Managing 10–15 clients without automatic expiry alerts is a real problem — finding out about an expired permit from the client themselves is the worst scenario. SmartPRO Hub sends 30-day and 7-day alerts for every permit for every client. If you want to see how it works, 15 minutes is enough.)*

---

**OA-006 · Sara Al-Lawati *(English)***
> Sara, thanks for connecting. Real-time Omanization ratio tracking is something most HR directors in Oman are still doing from last month's spreadsheet — which means you're managing risk with data that's already stale. SmartPRO Hub gives you a live dashboard: current ratio, headcount breakdown, what changes if one person leaves. Audit-ready on demand, not reconstructed after the fact. Worth 20 minutes to see?

---

**OA-007 · Hamad Al-Siyabi *(Arabic)***
> حمد، شكراً للتواصل. مشكلة التوسع في خدمات PRO حقيقية — كل عميل جديد يعني عبئاً تشغيلياً إضافياً طالما النظام يدوي. SmartPRO Hub يمكّن مكتب PRO من خدمة ٣٠–٤٠ عميلاً بنفس الفريق: تتبع المواعيد تلقائي، بوابة للعملاء يراجعون فيها حالة ملفاتهم، وفواتير تصدر عند إغلاق كل ملف. لو الهدف هو النمو بدون توظيف موظف لكل ٥ عملاء جدد، يستحق نكلم. ١٥ دقيقة تكفي.

*(Hamad, thanks for connecting. The PRO services scaling problem is real — every new client means extra operational burden as long as the system is manual. SmartPRO Hub lets a PRO office serve 30–40 clients with the same team: automatic deadline tracking, a client portal for case status, and invoices that go out when each case closes. If the goal is growth without hiring one person per five new clients, worth a conversation. 15 minutes is enough.)*

---

**OA-008 · Nadia Al-Tobi *(English)***
> Nadia, good to connect. The client visibility problem you described — updates via WhatsApp, clients feeling out of the loop — is exactly what SmartPRO Hub's client portal solves. Clients log in, see the live status of every case, download completed documents. The phone calls drop by 80%+ within the first month. For an independent consultant managing multiple clients, that's the difference between scalable and chaotic. Want me to show you the portal in 15 minutes?

---

**OA-009 · Yusuf Al-Kindi *(English)***
> Yusuf, thanks for connecting. Payroll errors that lead to employee disputes are almost always a WPS data issue — wrong IBANs, outdated records, bank formatting that silently rejects. SmartPRO Hub validates every record before submission: we flag the error before it becomes a dispute. For a group with multiple entities, we also give you one consolidated view across all payrolls. Happy to show you the validation layer specifically — 20 minutes.

---

**OA-010 · Mariam Al-Zadjali *(English)***
> Mariam, good to connect. Single-point-of-failure HR is a real risk — everything works until your one HR person is absent during payroll week. SmartPRO Hub puts all your HR data in a structured system anyone on your team can access: WPS history, leave records, permit status, employee contracts. No one person holds the keys. Worth 15 minutes to see what that looks like for a business your size?

---

**OA-011 · Ibrahim Al-Rawahi *(Arabic)***
> إبراهيم، شكراً للتواصل. تجديدات التصاريح الصناعية في صحار بحجم كبير — تتبعها يدوياً مع عملاء متعددين يعني أن فوات موعد واحد مسألة وقت. SmartPRO Hub يتابع كل تصريح لكل عميل ويُرسل تنبيهات قبل ٣٠ و٧ أيام. لو تريد ترى كيف يعمل مع حجم التصاريح عندك، ١٥ دقيقة تكفي.

*(Ibrahim, thanks for connecting. Industrial permit renewals in Sohar come in high volumes — tracking them manually across multiple clients means missing a deadline is a matter of time. SmartPRO Hub tracks every permit for every client and sends 30-day and 7-day alerts. If you want to see how it works with your permit volume, 15 minutes is enough.)*

---

**OA-012 · Ali Al-Ghafri *(English)***
> Ali, good to connect. Tracking 80+ expat work permits manually is where spreadsheets stop working — one missed renewal in a contracting environment isn't just an admin error, it's a compliance violation. SmartPRO Hub tracks every permit, fires alerts 30 and 7 days before expiry, and keeps the full renewal history for each employee. For a contracting company with high expat headcount, that's the difference between proactive and reactive compliance. Want to see it in 20 minutes?

---

**OA-013 · Bader Al-Maqbali *(English)***
> Bader, thanks for connecting. Month-end data that's weeks old when it reaches leadership is a structural problem — you're making growth decisions on a lagging picture. SmartPRO Hub gives you live HR and payroll data: headcount, WPS status, leave balances, permit expirations — all current. For a growth-stage business, that's the difference between seeing the road ahead and driving by the rear-view mirror. Happy to show you the dashboard in 20 minutes.

---

**OA-014 · Huda Al-Barwani *(English)***
> Huda, good to connect. Carrying HR and PRO responsibilities simultaneously is a real context-switch cost — they require completely different mental modes. SmartPRO Hub separates them cleanly: HR workflows (leave, contracts, payroll) on one side, PRO workflows (permits, Ministry filings, client cases) on the other, with one unified view when you need it. For someone wearing both hats, that structure matters. Want to see how it's set up in 15 minutes?

---

**OA-020 · Faisal Al-Hosni *(English)***
> Faisal, thanks for connecting. Managing HR and PRO compliance across multiple companies with no unified view is exactly the problem SmartPRO Hub was built to solve. One login: all entities, all employees, all permits, all WPS filings — with entity-level segmentation so nothing bleeds across. For a group operation, that consolidated view is the difference between managing by exception and managing by spreadsheet. Worth 20 minutes to see?

---

```python
python -c "
from outreach_tracker import advance_prospect
ids = ['OA-002','OA-003','OA-004','OA-005','OA-006','OA-007','OA-008',
       'OA-009','OA-010','OA-011','OA-012','OA-013','OA-014','OA-020']
[advance_prospect(i) for i in ids]
print('Step advanced for all 14')
"
```

---

## JUNE 10 — Segment A: Final Follow-up DMs (14 people · 30 min)

*Only send to those who accepted the connection but haven't replied to the June 5 DM.*

**English template:**
> [Name], wanted to follow up briefly. I shared the SmartPRO Hub demo link in my last message — if the timing wasn't right or the use case didn't fit, no problem at all. If it did resonate and you'd like to see it running, thesmartpro.io/demo books directly. Otherwise, good to be connected — I post on Oman HR and compliance regularly and you're welcome to that if it's useful.

**Arabic template:**
> [الاسم]، أردت المتابعة بإيجاز. شاركت رابط SmartPRO Hub في رسالتي السابقة — إن لم يكن الوقت مناسباً أو لم يكن موضوعنا ذا صلة، لا مشكلة على الإطلاق. لو أردت ترى النظام يعمل، thesmartpro.io/demo يتيح الحجز مباشرة. وإلا، يسعدني التواصل — أنشر بانتظام عن HR والامتثال في عُمان وأهلاً بك متابعتها.

```python
python -c "
from outreach_tracker import advance_prospect
ids = ['OA-002','OA-003','OA-004','OA-005','OA-006','OA-007','OA-008',
       'OA-009','OA-010','OA-011','OA-012','OA-013','OA-014','OA-020']
[advance_prospect(i) for i in ids]
print('Sequence complete for Seg A')
"
```

---

## SEQUENCE SUMMARY

| Date | Action | People | Time |
|------|--------|--------|------|
| May 28 ✅ | Like + comment | 20 | 30 min |
| May 30 | Connection request (no note) | 2 (Seg C) | 5 min |
| May 31 | Share post with note | 14 (Seg A) | 45 min |
| June 1 | Connection request with note | 3 (Seg B) | 10 min |
| June 1 | First DM | 2 (Seg C) | 10 min |
| June 3 | Connection request (no note) | 15 (Seg A) | 20 min |
| June 4 | DM + PDF attachment | 3 (Seg B) | 15 min |
| June 5 | First DM | 14 (Seg A) | 60 min |
| June 10 | Follow-up DM | 14 (Seg A) | 30 min |

**Total manual time across 14 days: ~3.75 hours**

---
*SmartPRO Hub Outreach System · Generated May 28, 2026*
