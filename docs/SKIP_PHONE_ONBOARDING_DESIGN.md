# Design: Skip Phone Verification During Onboarding

**Date:** 2026-03-18
**Status:** Approved, ready for implementation

---

## Understanding Summary

- **What:** A skip option at the phone number step in onboarding that bypasses phone entry, OTP verification, and WhatsApp opt-in in one action
- **Why:** Reduce onboarding friction; respect user privacy/preference without forcing a dead-end flow
- **Who:** All new users going through onboarding
- **Key constraint:** No new DB columns — `phone_verified = false && phone_number = null` is the signal throughout the app
- **Non-goals:** In-app banners outside the profile page; email nudges; permanent dismiss of nudge banner; differentiating "declined" vs "later" in storage

---

## Assumptions

1. "Dismissible" = per-session (reappears on next visit to `/profile`)
2. Alert icons persist until `phone_verified === true`
3. Skip confirmation is an assistant chat bubble in the onboarding flow, not a modal
4. Alert indicator is a small amber dot — new pattern for this codebase (no existing badge pattern to reuse)
5. Backend `_complete_onboarding` already handles null `phone_number` gracefully — no changes needed there

---

## Design

### 1. Backend — `backend/app/agents/onboarding.py`

**`_STEP_OPTIONS` for `phone_number` step:**

Add one skip option alongside the existing phone input:

```python
{"label": "Skip — I'll set SMS/WhatsApp notifications up later", "value": "__skip_phone__", "zod": "z.string()"}
```

**`_apply_extraction` / `onboarding_node`:**

When `step == "phone_number"` and `value == "__skip_phone__"`, mark all three phone-related tracking keys done in one shot:

```python
profile["_phone_collected"] = True
profile["_otp_done"] = True
profile["_whatsapp_answered"] = True
# phone_number intentionally left null
```

Return assistant message:
> "No problem — you can enable SMS and WhatsApp reminders anytime from your profile settings."

Then `_current_step` returns `None` → onboarding completes normally.

**No changes to `_complete_onboarding` or `_build_final_notification_preferences`** — null `phone_number` already handled.

---

### 2. Frontend — Alert Icons

**Condition (computed where user data is available):**
```ts
const needsPhoneSetup = !account.phone_verified && !account.notification_preferences?.phone_number;
```

**`frontend/src/components/navigation/BottomNav.tsx`**

Wrap the right nav item icon with an alert dot:
```tsx
<div className="relative">
  {rightItem.icon}
  {showPhoneAlert && (
    <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-amber-400" />
  )}
</div>
```

User data available via `useAuth()` (already in BottomNav context).

**`frontend/src/components/reflection/ProfileHeader.tsx`**

Add alert dot to the `SlidersHorizontal` gear icon link:
```tsx
<Link to="/profile" className="... relative">
  <SlidersHorizontal className="w-4 h-4 text-river" />
  {showPhoneAlert && (
    <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400" />
  )}
</Link>
```

Both dots disappear once `phone_verified === true`.

---

### 3. Frontend — Profile Page Nudge Banner

**`frontend/src/components/profile/ProfilePreferences.tsx`**

Per-session dismiss via `useState` (resets on every mount):
```tsx
const [phoneBannerDismissed, setPhoneBannerDismissed] = useState(false);

{needsPhoneSetup && !phoneBannerDismissed && (
  <div className="glass-card rounded-2xl px-4 py-3 flex items-start gap-3 mb-4">
    <span className="text-amber-400 mt-0.5"><AlertCircle className="w-4 h-4" /></span>
    <p className="text-sm text-white/70 flex-1">
      Set up your phone number to enable SMS and WhatsApp reminders.
    </p>
    <button onClick={() => setPhoneBannerDismissed(true)} className="text-white/40 hover:text-white/70">
      <X className="w-4 h-4" />
    </button>
  </div>
)}
```

Placed at the top of the Notifications section, above the phone verification UI.

---

### 4. Frontend — Disabled Notification Toggles

**`frontend/src/components/profile/ProfilePreferences.tsx`**

WhatsApp and phone call toggle rows visually disabled when `needsPhoneSetup`:
```tsx
<div className={needsPhoneSetup ? "opacity-40 pointer-events-none" : ""}>
  {/* existing WhatsApp toggle JSX */}
</div>

<div className={needsPhoneSetup ? "opacity-40 pointer-events-none" : ""}>
  {/* existing call toggle JSX */}
</div>

{needsPhoneSetup && (
  <p className="text-xs text-white/40 mt-1">Verify your phone number above to enable these.</p>
)}
```

Push notifications toggle is **unaffected**.

---

## Files to Change

| File | Change |
|------|--------|
| `backend/app/agents/onboarding.py` | Add skip option to `_STEP_OPTIONS`, handle `__skip_phone__` sentinel in step logic |
| `frontend/src/components/navigation/BottomNav.tsx` | Add alert dot to right nav item icon |
| `frontend/src/components/reflection/ProfileHeader.tsx` | Add alert dot to gear icon link |
| `frontend/src/components/profile/ProfilePreferences.tsx` | Add nudge banner + visually disable WhatsApp/call toggles |

---

## Decision Log

| # | Decision | Alternatives Considered | Why |
|---|----------|------------------------|-----|
| 1 | Single skip option: "Skip — I'll set SMS/WhatsApp notifications up later" | Two separate options (declined vs later) | Simpler UX, no storage differentiation needed |
| 2 | Skip at phone step collapses all 3 steps (phone + OTP + WhatsApp) | Skip each step individually | One action is less friction; no point asking WhatsApp without a phone |
| 3 | Sentinel value `__skip_phone__` flows through existing message pipeline | Pure frontend skip; dedicated endpoint | Reuses existing pipeline, avoids frontend encoding backend step logic |
| 4 | No new DB columns — existing nulls as signal | Store `phone_skipped` flag | YAGNI — existing nulls are sufficient signal |
| 5 | Skip confirmation is an assistant chat bubble | Modal, toast | Consistent with conversational onboarding style |
| 6 | Nudge banner is per-session dismissible (`useState`) | Permanent dismiss (DB flag); never dismissible | Balances persistence without being annoying or requiring new storage |
| 7 | Alert dot on Reflect tab right nav item | Add dedicated Profile tab | BottomNav already uses Reflect/Profile dynamically on the right slot |
| 8 | Toggles visually disabled (`opacity-40 pointer-events-none`) + hint text | Only functionally gated (existing behavior) | Makes dependency on phone setup explicit and discoverable |
