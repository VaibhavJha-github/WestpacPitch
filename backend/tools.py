"""LLM-callable tools for the voice agent orchestration."""
import asyncio
from db import get_supabase
from datetime import datetime, timedelta
import config


def get_customer_profile(customer_id: str) -> dict | None:
    sb = get_supabase()
    res = sb.table("customer_profiles").select("*").eq("id", customer_id).execute()
    return res.data[0] if res.data else None


def get_customer_accounts(customer_id: str) -> list[dict]:
    sb = get_supabase()
    res = sb.table("customer_accounts").select("*").eq("customer_id", customer_id).execute()
    return res.data


def get_customer_transactions(customer_id: str, days: int = 90) -> list[dict]:
    sb = get_supabase()
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    res = (
        sb.table("customer_transactions")
        .select("*")
        .eq("customer_id", customer_id)
        .gte("posted_at", since)
        .order("posted_at", desc=True)
        .execute()
    )
    return res.data


def get_spending_summary(customer_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("v_transaction_categories")
        .select("*")
        .eq("customer_id", customer_id)
        .execute()
    )
    return res.data


def search_knowledge_pack(query: str) -> list[dict]:
    sb = get_supabase()
    # Simple text search — for demo, search title and content via ilike
    res = (
        sb.table("knowledge_documents")
        .select("slug, title, content, source_label")
        .or_(f"title.ilike.%{query}%,content.ilike.%{query}%")
        .limit(3)
        .execute()
    )
    return res.data


def get_available_banker_slots(date_str: str | None = None) -> list[dict]:
    sb = get_supabase()
    query = (
        sb.table("banker_availability")
        .select("*, bankers(display_name, role_title, region)")
        .eq("status", "available")
        .order("starts_at")
    )
    if date_str:
        query = query.gte("starts_at", f"{date_str}T00:00:00").lte("starts_at", f"{date_str}T23:59:59")
    res = query.execute()
    return res.data


def hold_slot(slot_id: str, slot_type: str) -> dict:
    sb = get_supabase()
    status = "primary_selected" if slot_type == "primary" else "fallback_selected"
    res = (
        sb.table("banker_availability")
        .update({"status": status})
        .eq("id", slot_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def create_appointment(data: dict) -> dict:
    sb = get_supabase()
    res = sb.table("appointments").insert(data).execute()
    return res.data[0] if res.data else {}


def accept_appointment_slot(appointment_id: str, slot_id: str) -> dict:
    sb = get_supabase()
    # Update appointment
    sb.table("appointments").update({
        "confirmed_slot_id": slot_id,
        "status": "Upcoming",
    }).eq("id", appointment_id).execute()

    # Update slot status
    sb.table("banker_availability").update({"status": "booked"}).eq("id", slot_id).execute()

    # Release the other slot if any
    apt = sb.table("appointments").select("preferred_slot_id, fallback_slot_id").eq("id", appointment_id).execute()
    if apt.data:
        apt_data = apt.data[0]
        other_slot = apt_data.get("fallback_slot_id") if slot_id == apt_data.get("preferred_slot_id") else apt_data.get("preferred_slot_id")
        if other_slot and other_slot != slot_id:
            sb.table("banker_availability").update({"status": "available"}).eq("id", other_slot).execute()

    return {"status": "accepted", "slot_id": slot_id}


def route_to_team(intent: str, emotion: str | None = None) -> str:
    intent_lower = intent.lower()
    if any(kw in intent_lower for kw in ["fraud", "scam", "suspicious", "lost card", "stolen"]):
        return "Security Specialist Team"
    if any(kw in intent_lower for kw in ["hardship", "difficulty", "can't pay", "struggling"]):
        return "Financial Hardship"
    if any(kw in intent_lower for kw in ["home loan", "mortgage", "refinanc", "first home", "property", "deposit", "pre-approval", "fixed rate"]):
        return "Home Loans / Mortgages"
    if any(kw in intent_lower for kw in ["business loan", "commercial", "expansion"]):
        return "Personal Loans"
    if any(kw in intent_lower for kw in ["card", "payment", "credit card"]):
        return "Cards & Payments"
    if any(kw in intent_lower for kw in ["account", "transaction", "transfer", "balance"]):
        return "Transactions & Accounts"
    if any(kw in intent_lower for kw in ["app", "online", "digital", "login", "password"]):
        return "Digital Banking Support"
    if any(kw in intent_lower for kw in ["dispute", "chargeback", "unauthorized"]):
        return "Disputes / Chargebacks"
    return "Home Loans / Mortgages"


def save_call_session(session_data: dict) -> dict:
    sb = get_supabase()
    res = sb.table("call_sessions").insert(session_data).execute()
    return res.data[0] if res.data else {}


def update_call_session(session_id: str, data: dict) -> dict:
    sb = get_supabase()
    res = sb.table("call_sessions").update(data).eq("id", session_id).execute()
    return res.data[0] if res.data else {}


def save_call_turn(turn_data: dict) -> dict:
    sb = get_supabase()
    res = sb.table("call_turns").insert(turn_data).execute()
    return res.data[0] if res.data else {}


def update_analytics(metrics: dict) -> dict:
    sb = get_supabase()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    existing = sb.table("analytics_snapshots").select("id").eq("snapshot_date", today).execute()
    if existing.data:
        res = sb.table("analytics_snapshots").update(metrics).eq("id", existing.data[0]["id"]).execute()
    else:
        metrics["snapshot_date"] = today
        res = sb.table("analytics_snapshots").insert(metrics).execute()
    return res.data[0] if res.data else {}


# ============================================================
# SMS via Twilio
# ============================================================

def send_sms(to: str, body: str) -> dict:
    """Send an SMS via Twilio. Returns message SID or error."""
    if not config.TWILIO_ACCOUNT_SID or not config.TWILIO_AUTH_TOKEN:
        print(f"[SMS] Twilio not configured. Would send to {to}: {body}")
        return {"status": "skipped", "reason": "twilio_not_configured", "body": body}

    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=config.TWILIO_PHONE_NUMBER,
            to=to,
        )
        print(f"[SMS] Sent to {to}: {message.sid}")
        return {"status": "sent", "sid": message.sid}
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return {"status": "error", "error": str(e)}


def send_booking_confirmation_sms(appointment_id: str) -> dict:
    """Send booking confirmation + cross-sell SMS after banker accepts."""
    sb = get_supabase()
    apt = sb.table("appointments").select("*").eq("id", appointment_id).execute()
    if not apt.data:
        return {"status": "error", "error": "appointment not found"}

    apt_data = apt.data[0]
    customer_name = (apt_data.get("customer_name") or "there").split()[0]
    location_type = apt_data.get("location_type", "Phone")

    # Get confirmed slot time
    slot_label = ""
    slot_id = apt_data.get("confirmed_slot_id") or apt_data.get("preferred_slot_id")
    if slot_id:
        slot = sb.table("banker_availability").select("slot_label, starts_at").eq("id", slot_id).execute()
        if slot.data:
            slot_label = slot.data[0].get("slot_label", "")

    # Determine phone number to send to
    to_number = config.CUSTOMER_PHONE_NUMBER
    if not to_number:
        print("[SMS] No customer phone configured (CUSTOMER_PHONE_NUMBER)")
        return {"status": "skipped", "reason": "no_customer_phone"}

    # Message 1: Booking confirmation
    if location_type in ("In-branch", "Mobile lender visit"):
        confirm_msg = (
            f"Hi {customer_name}! Your appointment with Rob at Westpac has been confirmed. "
            f"Time: {slot_label}. "
            f"Location: Westpac Brisbane City, 260 Queen Street, Brisbane QLD 4000. "
            f"See you there! - Westpac"
        )
    else:
        confirm_msg = (
            f"Hi {customer_name}! Your appointment with Rob at Westpac has been confirmed. "
            f"Time: {slot_label}. "
            f"Join your video meeting here: https://teams.microsoft.com/westpac-demo-link "
            f"- Westpac"
        )

    result1 = send_sms(to_number, confirm_msg)

    # Message 2: Cross-sell (sent after a short delay)
    crosssell_msg = (
        f"Hi {customer_name}! Since you're looking into a home loan, "
        f"we have some exclusive Westpac customer deals on home insurance "
        f"that pair perfectly with your new loan. "
        f"Check them out: https://westpac.com.au/home-insurance-deals "
        f"- Westpac"
    )

    return {"confirmation": result1, "crosssell_body": crosssell_msg, "to": to_number}


async def send_crosssell_sms_delayed(to: str, body: str, delay_seconds: int = 10):
    """Send cross-sell SMS after a delay (async)."""
    await asyncio.sleep(delay_seconds)
    send_sms(to, body)


def create_appointment_from_call(
    session_id: str,
    customer_id: str,
    intent: str,
    location_type: str,
    ai_note: str,
    collected_data: list[dict] | None = None,
    primary_slot_id: str | None = None,
    fallback_slot_id: str | None = None,
) -> dict:
    """Create an appointment from a live call. Status = Pending until banker accepts."""
    sb = get_supabase()

    # Get customer profile for denormalized fields
    profile = get_customer_profile(customer_id)
    if not profile:
        return {"status": "error", "error": "customer not found"}

    # Get banker (Rob)
    banker_id = "b0000001-0000-0000-0000-000000000001"

    apt_data = {
        "customer_id": customer_id,
        "session_id": session_id,
        "banker_id": banker_id,
        "appointment_type": intent,
        "location_type": location_type,
        "intent": intent,
        "ai_note": ai_note,
        "status": "Pending",
        "customer_name": profile["full_name"],
        "customer_initials": profile.get("initials", ""),
        "customer_tenure": profile.get("tenure_label", ""),
        "age": profile.get("age"),
        "location": profile.get("location", ""),
        "profession": profile.get("profession", ""),
        "total_banking_value": profile.get("banking_value_label", ""),
        "collected_data_json": collected_data or [],
    }

    if primary_slot_id:
        apt_data["preferred_slot_id"] = primary_slot_id
        hold_slot(primary_slot_id, "primary")
    if fallback_slot_id:
        apt_data["fallback_slot_id"] = fallback_slot_id
        hold_slot(fallback_slot_id, "fallback")

    res = sb.table("appointments").insert(apt_data).execute()
    if res.data:
        print(f"[BOOKING] Created appointment {res.data[0]['id']} (Pending)")
    return res.data[0] if res.data else {}
