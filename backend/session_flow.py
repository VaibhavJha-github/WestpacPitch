import json
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

import config
from db import get_supabase
from llm import generate_response, generate_summary
from sentiment import aggregate_sentiment
from stt import transcribe_audio
from tools import (
    create_appointment_from_call,
    get_available_banker_slots,
    get_customer_accounts,
    get_customer_profile,
    get_spending_summary,
    route_to_team,
    save_call_session,
    save_call_turn,
    search_knowledge_pack,
    send_sms,
    update_analytics,
    update_call_session,
)


class SessionFlow:
    def __init__(self, customer_id: str = "c0000001-0000-0000-0000-000000000001"):
        self.session_id = str(uuid4())
        self.customer_id = customer_id
        self.turn_index = 0
        self.messages = []
        self.all_turns = []
        self.booking_created = False
        self.profile = None
        self.accounts = []
        self.context = ""
        self.preferred_location_type = "Phone"

    async def start(self) -> dict:
        self._resolve_customer()

        save_call_session({
            "id": self.session_id,
            "customer_id": self.customer_id,
            "session_status": "active",
        })

        customer_name = self.profile["full_name"].split()[0] if self.profile else "mate"
        greeting = (
            f"G'day {customer_name}, thanks for calling Westpac! "
            "I'm Alex, your AI assistant. How can I help you today?"
        )

        self.messages.append({"role": "assistant", "content": greeting})
        self.all_turns.append({"speaker": "bot", "text": greeting, "lang": "en"})

        return {
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "greeting": greeting,
        }

    async def process_audio(self, audio_bytes: bytes, filename: str) -> dict | None:
        stt_result = transcribe_audio(audio_bytes, filename=filename)
        stt_latency = stt_result["latency_ms"]
        customer_text = stt_result["text"].strip()
        print(f"[STT] {stt_latency}ms: '{customer_text}'")

        if not customer_text:
            return None

        if len(customer_text.split()) < 2:
            print(f"[STT] Skipping single word: {customer_text}")
            return None

        self.turn_index += 1
        self.all_turns.append({
            "speaker": "customer",
            "text": customer_text,
            "lang": "en",
            "stt_ms": stt_latency,
        })
        self.messages.append({"role": "user", "content": customer_text})

        extra_context = self._build_extra_context(customer_text)
        trimmed_messages = self.messages[-10:] if len(self.messages) > 10 else self.messages

        try:
            llm_result = await generate_response(trimmed_messages, context=extra_context)
        except Exception as e:
            print(f"[LLM ERROR] {e}")
            llm_result = {
                "text": "Sorry, could you say that again mate?",
                "latency_ms": 0,
                "provider": "fallback",
            }

        llm_latency = llm_result["latency_ms"]
        bot_text = llm_result["text"]
        print(f"[LLM] {llm_result.get('provider', '?')} {llm_latency}ms: {bot_text[:80]}")

        if llm_result.get("tool_call"):
            bot_text, llm_latency = await self._handle_tool_call(
                llm_result=llm_result,
                bot_text=bot_text,
                llm_latency=llm_latency,
                extra_context=extra_context,
            )

        if not bot_text:
            bot_text = "I understand. How can I help you further?"

        self.messages.append({"role": "assistant", "content": bot_text})
        self.turn_index += 1
        self.all_turns.append({
            "speaker": "bot",
            "text": bot_text,
            "lang": "en",
            "llm_ms": llm_latency,
        })

        return {
            "customer_text": customer_text,
            "bot_text": bot_text,
            "stt_latency_ms": stt_latency,
            "llm_latency_ms": llm_latency,
            "turn_index": self.turn_index,
            "language": "en",
        }

    async def finalize(self) -> dict | None:
        if not self.all_turns:
            return None

        print(f"[POST-CALL] Processing {len(self.all_turns)} turns...")

        for i, turn in enumerate(self.all_turns):
            save_call_turn({
                "session_id": self.session_id,
                "speaker": turn["speaker"],
                "text": turn["text"],
                "timestamp_label": datetime.now(timezone.utc).strftime("%H:%M"),
                "language_code": turn.get("lang", "en"),
                "turn_index": i + 1,
                "stt_latency_ms": turn.get("stt_ms"),
                "llm_latency_ms": turn.get("llm_ms"),
                "tts_latency_ms": turn.get("tts_ms"),
            })

        customer_texts = [t["text"] for t in self.all_turns if t["speaker"] == "customer"]
        agg = aggregate_sentiment([
            {"speaker": "customer", "text": text}
            for text in customer_texts
        ])

        summary = await generate_summary(self.all_turns)
        summary = self._normalize_summary(summary)

        sb = get_supabase()
        existing_apt = (
            sb.table("appointments")
            .select("id")
            .eq("session_id", self.session_id)
            .limit(1)
            .execute()
        )
        if existing_apt.data:
            self.booking_created = True

        if not self.booking_created:
            await self._maybe_create_fallback_booking(summary)

        update_call_session(self.session_id, {
            "session_status": "completed",
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "sentiment_label": agg["label"],
            "sentiment_score": agg["score"],
            "emotion_summary": agg["emotion"],
            "primary_intent": summary.get("primary_intent", ""),
            "routed_team": summary.get("routed_team", ""),
            "ai_summary_short": summary.get("short_summary", ""),
            "ai_summary_long": summary.get("long_summary", ""),
            "recommended_strategy_title": summary.get("recommended_strategy_title", ""),
            "recommended_strategy_description": summary.get("recommended_strategy_description", ""),
        })

        try:
            apts = (
                sb.table("appointments")
                .select("id")
                .eq("session_id", self.session_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if apts.data:
                apt_id = apts.data[0]["id"]
                appt_update = {
                    "appointment_type": summary.get("primary_intent") or "Home Loan Enquiry",
                    "intent": summary.get("primary_intent") or "Home Loan Enquiry",
                    "location_type": self.preferred_location_type,
                    "ai_note": summary.get("short_summary") or summary.get("long_summary") or "",
                    "recommended_strategy_title": summary.get("recommended_strategy_title", ""),
                    "recommended_strategy_description": summary.get("recommended_strategy_description", ""),
                    "sentiment": agg.get("label", "Neutral"),
                    "sentiment_score": agg.get("score", 50),
                    "sentiment_note": summary.get("sentiment_note") or agg.get("emotion", ""),
                }
                collected = summary.get("collected_data")
                if isinstance(collected, list):
                    appt_update["collected_data_json"] = collected
                sb.table("appointments").update(appt_update).eq("id", apt_id).execute()
                print(f"[POST-CALL] Enriched appointment {apt_id} from summary")
        except Exception as e:
            print(f"[POST-CALL] Failed to enrich appointment: {e}")

        try:
            update_analytics({
                "total_calls": 1,
                "completed_appointments": 1 if self.booking_created else 0,
            })
        except Exception:
            pass

        print(f"[POST-CALL] Done. Sentiment: {agg['label']}, Intent: {summary.get('primary_intent')}")
        return {
            "session_id": self.session_id,
            "summary": summary,
            "sentiment": agg,
            "booking_created": self.booking_created,
        }

    def _resolve_customer(self) -> None:
        self.profile = get_customer_profile(self.customer_id)
        if not self.profile:
            sb = get_supabase()
            fallback_customer = (
                sb.table("customer_profiles")
                .select("id, full_name, age, location, profession, tenure_label")
                .limit(1)
                .execute()
            )
            if fallback_customer.data:
                self.profile = fallback_customer.data[0]
                self.customer_id = self.profile["id"]
                print(f"[SESSION] Using fallback customer_id={self.customer_id}")
            else:
                print("[SESSION] No customer profile found; continuing without profile context")

        self.accounts = get_customer_accounts(self.customer_id)
        context_parts = []
        if self.profile:
            context_parts.append(
                f"Customer: {self.profile['full_name']}, Age: {self.profile.get('age')}, "
                f"Location: {self.profile.get('location')}, Profession: {self.profile.get('profession')}, "
                f"Tenure: {self.profile.get('tenure_label')}"
            )
        if self.accounts:
            acct_summary = ", ".join(f"{a['nickname']}: ${a['balance']}" for a in self.accounts)
            context_parts.append(f"Accounts: {acct_summary}")
        self.context = "\n".join(context_parts)

    def _build_extra_context(self, customer_text: str) -> str:
        extra_context = self.context

        for kw in [
            "rate", "loan", "product", "home loan", "fixed", "variable",
            "first home", "fraud", "scam", "lost card",
        ]:
            if kw in customer_text.lower():
                knowledge = search_knowledge_pack(kw)
                if knowledge:
                    extra_context += "\n\nRelevant Knowledge:\n" + "\n---\n".join(
                        f"{k['title']}: {k['content'][:500]}" for k in knowledge
                    )
                break

        for kw in [
            "spend", "saving", "budget", "afford", "money", "car",
            "goal", "coffee", "eating out",
        ]:
            if kw in customer_text.lower():
                spending = get_spending_summary(self.customer_id)
                if spending:
                    extra_context += "\n\nSpending Summary:\n" + "\n".join(
                        f"- {s['category']}: ${s['total_amount']} ({s['transaction_count']} txns, avg ${s['avg_amount']})"
                        for s in spending
                    )
                break

        return extra_context

    async def _handle_tool_call(self, llm_result: dict, bot_text: str, llm_latency: int, extra_context: str) -> tuple[str, int]:
        tc = llm_result["tool_call"]
        tool_name = tc.get("tool", "")
        tool_args = tc.get("args", {})
        print(f"[TOOL] {tool_name} args={tool_args}")

        if tool_name == "get_available_banker_slots":
            tool_result = get_available_banker_slots(tool_args.get("date"))
            if tool_result:
                slots_text = "\n".join(f"- {s['slot_label']} ({s['status']})" for s in tool_result[:5])
                self.messages.append({"role": "assistant", "content": bot_text or "Let me check available slots."})
                self.messages.append({
                    "role": "user",
                    "content": f"[Tool result - available slots:\n{slots_text}]\nNow offer the customer 2 suitable slots from this list.",
                })
                followup = await generate_response(self.messages, context=extra_context)
                return followup["text"], llm_latency + followup["latency_ms"]

        elif tool_name == "search_knowledge_pack":
            tool_result = search_knowledge_pack(tool_args.get("query", ""))
            if tool_result:
                knowledge_text = "\n---\n".join(f"{k['title']}: {k['content'][:400]}" for k in tool_result)
                self.messages.append({"role": "assistant", "content": bot_text or "Let me look that up."})
                self.messages.append({
                    "role": "user",
                    "content": f"[Knowledge result:\n{knowledge_text}]\nAnswer the customer's question using this information.",
                })
                followup = await generate_response(self.messages, context=extra_context)
                return followup["text"], llm_latency + followup["latency_ms"]

        elif tool_name == "create_appointment_offer":
            convo_text = " ".join(
                t.get("text", "") for t in self.all_turns if t.get("speaker") == "customer"
            )
            location_type = self._normalize_location_type(tool_args.get("location_type"), convo_text)
            apt = create_appointment_from_call(
                session_id=self.session_id,
                customer_id=self.customer_id,
                intent=self._normalize_intent(tool_args.get("intent"), convo_text),
                location_type=location_type,
                ai_note=self._clean_summary_text(tool_args.get("ai_note", "")),
                collected_data=self._normalize_collected_data(tool_args.get("collected_data"), convo_text),
                primary_slot_id=tool_args.get("primary_slot_id"),
                fallback_slot_id=tool_args.get("fallback_slot_id"),
                conversation_text=convo_text,
            )
            if apt and apt.get("id"):
                self.booking_created = True
                self.preferred_location_type = location_type

        elif tool_name == "send_followup_sms":
            sms_body = tool_args.get("message", "")
            if sms_body and config.CUSTOMER_PHONE_NUMBER:
                send_sms(config.CUSTOMER_PHONE_NUMBER, sms_body)

        elif tool_name == "route_to_team":
            team = route_to_team(tool_args.get("intent", ""), tool_args.get("emotion"))
            update_call_session(self.session_id, {"routed_team": team})

        elif tool_name == "get_spending_summary":
            tool_result = get_spending_summary(tool_args.get("customer_id", self.customer_id))
            if tool_result:
                spending_text = "\n".join(
                    f"- {s['category']}: ${s['total_amount']} ({s['transaction_count']} txns)"
                    for s in tool_result
                )
                self.messages.append({"role": "assistant", "content": bot_text or "Let me review your spending."})
                self.messages.append({
                    "role": "user",
                    "content": f"[Spending data:\n{spending_text}]\nProvide helpful spending insights to the customer.",
                })
                followup = await generate_response(self.messages, context=extra_context)
                return followup["text"], llm_latency + followup["latency_ms"]

        return bot_text, llm_latency

    async def _maybe_create_fallback_booking(self, summary: dict) -> None:
        customer_utterances = [
            t["text"].lower() for t in self.all_turns
            if t.get("speaker") == "customer" and t.get("text")
        ]
        bot_utterances = [
            t["text"].lower() for t in self.all_turns
            if t.get("speaker") == "bot" and t.get("text")
        ]
        conversation_text = " ".join(customer_utterances)
        bot_text = " ".join(bot_utterances)

        booking_intent = any(
            kw in conversation_text
            for kw in [
                "book", "booking", "meeting", "appointment",
                "speak to a banker", "specialist", "can i meet",
            ]
        )

        scheduling_signals = sum(
            1 for kw in [
                "as soon as possible", "tomorrow", "today", "next week",
                "8 to 9", "12 to 1", "3 to 4", "morning", "afternoon",
                "online", "video", "in person", "in-branch",
            ] if kw in conversation_text
        )
        bot_booking_language = any(
            kw in bot_text
            for kw in [
                "you're all sorted", "i'll set up", "i've got rob",
                "once rob confirms", "would you prefer to meet", "openings",
            ]
        )
        booking_intent = booking_intent or (scheduling_signals >= 2 and bot_booking_language)

        if not booking_intent:
            print(
                f"[BOOKING FALLBACK] Skipped. booking_intent=False, "
                f"scheduling_signals={scheduling_signals}, bot_booking_language={bot_booking_language}"
            )
            return

        location_type = self._normalize_location_type(summary.get("location_type"), conversation_text)
        self.preferred_location_type = location_type

        slots = get_available_banker_slots()
        primary_slot_id = slots[0]["id"] if len(slots) > 0 else None
        fallback_slot_id = slots[1]["id"] if len(slots) > 1 else None

        fallback_intent = self._normalize_intent(summary.get("primary_intent"), conversation_text)

        fallback_note = self._clean_summary_text(
            summary.get("short_summary") or summary.get("long_summary") or "Auto-created from live call booking intent."
        )
        apt = create_appointment_from_call(
            session_id=self.session_id,
            customer_id=self.customer_id,
            intent=fallback_intent,
            location_type=location_type,
            ai_note=fallback_note,
            collected_data=self._normalize_collected_data(summary.get("collected_data", []), conversation_text),
            primary_slot_id=primary_slot_id,
            fallback_slot_id=fallback_slot_id,
            conversation_text=conversation_text,
        )

        if apt and apt.get("id"):
            self.booking_created = True
            print(f"[BOOKING FALLBACK] Auto-created appointment {apt['id']} from booking intent")
        else:
            print("[BOOKING FALLBACK] Booking intent detected but appointment creation failed")

    def _normalize_summary(self, summary: dict | None) -> dict:
        summary = summary or {}
        conversation_text = " ".join(
            t.get("text", "") for t in self.all_turns if t.get("speaker") == "customer"
        )

        primary_intent = self._normalize_intent(summary.get("primary_intent"), conversation_text)
        collected_data = self._normalize_collected_data(summary.get("collected_data"), conversation_text)
        short_summary = self._clean_summary_text(summary.get("short_summary") or summary.get("long_summary") or "")
        long_summary = self._clean_summary_text(summary.get("long_summary") or short_summary)

        if not short_summary:
            short_summary = f"Customer called about {primary_intent.lower()} and needs follow-up from a specialist."
        if not long_summary:
            long_summary = short_summary

        self.preferred_location_type = self._normalize_location_type(summary.get("location_type"), conversation_text)

        return {
            "short_summary": short_summary,
            "long_summary": long_summary,
            "primary_intent": primary_intent,
            "routed_team": summary.get("routed_team") or route_to_team(primary_intent, summary.get("sentiment_note")),
            "recommended_strategy_title": summary.get("recommended_strategy_title") or "Customer Needs Review",
            "recommended_strategy_description": summary.get("recommended_strategy_description") or long_summary,
            "collected_data": collected_data,
            "sentiment_label": summary.get("sentiment_label") or "Neutral",
            "sentiment_note": summary.get("sentiment_note") or "",
            "follow_up_actions": summary.get("follow_up_actions") or [],
            "location_type": self.preferred_location_type,
        }

    def _normalize_intent(self, raw_intent: str | None, conversation_text: str) -> str:
        intent = (raw_intent or "").strip()
        if intent and "unknown" not in intent.lower():
            return intent

        text = conversation_text.lower()
        if any(term in text for term in ["first home", "buy my first home", "buying my first home", "first-time buyer"]):
            return "First Home Purchase"
        if any(term in text for term in ["home loan", "mortgage", "property", "deposit", "pre approval", "pre-approval"]):
            return "Home Loan Enquiry"
        if any(term in text for term in ["refinance", "fixed rate ending", "fixed rate is ending"]):
            return "Refinance - Fixed Rate Expiry"
        if any(term in text for term in ["fraud", "scam", "lost card", "stolen card"]):
            return "Fraud or Card Security"
        return "Home Loan Enquiry"

    def _normalize_location_type(self, raw_location: str | None, conversation_text: str) -> str:
        text = f"{raw_location or ''} {conversation_text}".lower()
        if any(term in text for term in ["video", "online", "zoom", "teams", "video call", "video chat"]):
            return "Video chat"
        if any(term in text for term in ["in person", "in-branch", "at branch", "branch"]):
            return "In-branch"
        if any(term in text for term in ["mobile lender", "meet me", "come to me"]):
            return "Mobile lender visit"
        return "Phone"

    def _clean_summary_text(self, text: str | None) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                cleaned = parsed.get("short_summary") or parsed.get("long_summary") or cleaned
        except Exception:
            if "{" in cleaned and "}" in cleaned and "short_summary" in cleaned:
                try:
                    start = cleaned.index("{")
                    end = cleaned.rindex("}") + 1
                    parsed = json.loads(cleaned[start:end])
                    if isinstance(parsed, dict):
                        cleaned = parsed.get("short_summary") or parsed.get("long_summary") or cleaned
                except Exception:
                    pass

        cleaned = re.sub(r'^\s*\{?\s*"?short_summary"?\s*:\s*"?', "", cleaned).strip()
        cleaned = re.sub(r'"?\s*\}?\s*$', "", cleaned).strip()

        lower = cleaned.lower()
        cut_markers = [
            "he has been booked",
            "she has been booked",
            "they have been booked",
            "customer has been booked",
            "appointment booked",
            "video call with",
            "phone call with",
        ]
        for marker in cut_markers:
            idx = lower.find(marker)
            if idx > 0:
                cleaned = cleaned[:idx].rstrip(" ,.-") + "."
                break

        return cleaned.strip()

    def _normalize_collected_data(self, raw_data, conversation_text: str) -> list[dict]:
        normalized = []

        if isinstance(raw_data, dict):
            for key, value in raw_data.items():
                if value:
                    normalized.append({"label": str(key), "value": str(value)})
        elif isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    label = item.get("label") or item.get("key") or item.get("name")
                    value = item.get("value") or item.get("answer") or item.get("detail")
                    if label and value:
                        normalized.append({"label": str(label), "value": str(value)})

        if normalized:
            return normalized

        facts = []
        text = conversation_text
        lower = text.lower()

        money_values = re.findall(r'\$[\d,]+(?:\.\d+)?\s*(?:million|m|k)?', text, flags=re.IGNORECASE)
        property_price_match = re.search(
            r'(?:buy|purchase|purchasing|looking to buy|looking to purchase)[^$.\n]{0,60}(\$[\d,]+(?:\.\d+)?\s*(?:million|m|k)?)',
            text,
            flags=re.IGNORECASE,
        )
        saved_match = re.search(
            r'(?:saved up|saved|deposit(?: of)?|have)\s*(\$[\d,]+(?:\.\d+)?\s*(?:million|m|k)?)',
            text,
            flags=re.IGNORECASE,
        )

        if property_price_match:
            facts.append({"label": "Target Property Price", "value": property_price_match.group(1)})
        if saved_match:
            facts.append({"label": "Available Deposit", "value": saved_match.group(1)})
        if money_values:
            if not property_price_match and not saved_match:
                facts.append({"label": "Amount Discussed", "value": money_values[0]})
            if len(money_values) > 1 and len(facts) < 3:
                facts.append({"label": "Additional Financial Figure", "value": money_values[1]})

        if "gold coast" in lower:
            facts.append({"label": "Target Location", "value": "Gold Coast"})
        if any(term in lower for term in ["video", "online", "zoom", "teams"]):
            facts.append({"label": "Meeting Preference", "value": "Video chat"})
        elif any(term in lower for term in ["in person", "branch", "in-branch"]):
            facts.append({"label": "Meeting Preference", "value": "In-branch"})

        if "first home" in lower:
            facts.append({"label": "Buyer Profile", "value": "First home buyer"})
        elif "home loan" in lower or "mortgage" in lower:
            facts.append({"label": "Product Interest", "value": "Home loan"})

        return facts