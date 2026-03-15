# Design: "Change Number" Option on Onboarding OTP Step

**Date**: 2026-03-15
**Status**: Approved, ready for implementation

---

## Understanding Summary

- **What**: A "Change number" secondary button on the OTP verification step during onboarding
- **Why**: Users who typed the wrong number (or want a different one) are stuck at OTP with no way back
- **Who**: New users going through onboarding for the first time
- **Key constraints**: Minimal surface area — reuse existing phone submission and OTP paths
- **Non-goals**: No change to Settings phone verification flow; no "change number" on the phone input step itself; no change to max attempts per number (still 3)

---

## Assumptions

1. The OTP step already shows the number the code was sent to — confirmed in `OtpInput` component
2. Changing the number re-triggers `send_otp()` automatically via the normal phone submission path
3. The backend resets `_otp_attempts` when a new phone number is submitted
4. No new API endpoint needed

---

## Decision Log

| # | Decision | Alternatives Considered | Rationale |
|---|----------|------------------------|-----------|
| 1 | "Change number" appears only on OTP step | Also on phone input step | YAGNI — need arises after submission, not before |
| 2 | Secondary button alongside "Resend code" | Text link, inline with phone display | More discoverable; clear visual hierarchy |
| 3 | Empty field on return | Pre-filled with previous number | Clean slate avoids re-submitting the wrong number |
| 4 | Attempt counter resets on new number | Keep counter across numbers | Punishing a typo with fewer attempts is bad UX |
| 5 | Client-side step navigation (cache phone options in `useRef`) | Sentinel message to backend | No extra API surface; reuses existing submission path |
| 6 | Backend resets `_otp_attempts` on re-entry | No backend change | Keeps server-side attempt count consistent with frontend |

---

## Final Design

### Frontend

#### 1. `OtpInput` — `frontend/src/components/chat/OnboardingOptions.tsx`

- Add prop: `onChangeNumber: () => void`
- Add a "Change number" ghost/secondary button in the same row as "Resend code"
- Button hierarchy:
  - Primary: "Verify"
  - Secondary: "Resend code" | "Change number"
- No confirmation dialog on click — low-stakes navigation

#### 2. `OnboardingOptions` — same file

- Thread `onChangeNumber` prop down to `OtpInput`

#### 3. `OnboardingChat` — `frontend/src/components/onboarding/OnboardingChat.tsx`

- When user advances past the phone step, cache the phone step options in a `useRef`
- Add `handleChangeNumber()`:
  - Restores cached phone step options
  - Clears current OTP input state
  - No network call
- Pass `handleChangeNumber` through `OnboardingOptions` → `OtpInput`

---

### Backend

#### `onboarding_node` — `backend/app/agents/onboarding.py`

When a phone number is received and `_phone_collected` is already `True` (re-entry):

```python
profile["_otp_attempts"] = 0
profile["_otp_done"] = False  # defensive, already False
```

This ensures the server-side attempt counter is reset for the new number.
All other logic (overwrite stored phone number, call `send_otp()`) already works via the existing path.

---

## Implementation Checklist

- [ ] Add `onChangeNumber` prop to `OtpInput` and `OnboardingOptions`
- [ ] Add "Change number" secondary button to `OtpInput` UI
- [ ] Add `phoneStepOptionsRef` and `handleChangeNumber` to `OnboardingChat`
- [ ] Wire `handleChangeNumber` through props
- [ ] Add attempt counter reset in `onboarding_node` on phone re-entry
- [ ] Manual test: submit wrong number → OTP step → Change number → submit new number → verify OTP resets
