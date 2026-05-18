"""
Pipeline con SSE streaming.
Mejora Arquitectura B: A2 y A3 corren en paralelo con asyncio.gather.
"""
import asyncio
import json
from typing import AsyncGenerator

from orchestrator.conversation_memory import ConversationMemory, get_or_create
from orchestrator.state_machine import ConversationState
from orchestrator.token_budget import TokenBudgetManager
from agents.agent_symptom import SymptomInterpreter
from agents.agent_specialty import SpecialtySuggester
from agents.agent_policy import PolicyLookup
from agents.agent_copay import CopayCalculator
from agents.agent_hospital import HospitalRanker
from agents.agent_summary import SummaryWriter
from orchestrator.copay_validator import validate as validate_copay
from orchestrator.episode_predictor import predict_episode
from services.forecast_service import save_episode_prediction
from db.rls import make_session_hash

_a1 = SymptomInterpreter()
_a2 = SpecialtySuggester()
_a3 = PolicyLookup()
_a4 = CopayCalculator()
_a5 = HospitalRanker()
_a6 = SummaryWriter()

_budgets: dict[str, TokenBudgetManager] = {}


def _event(kind: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': kind, **payload})}\n\n"


async def process_message(
    session_id: str,
    conversation_id: str | None,
    user_message: str,
) -> AsyncGenerator[str, None]:
    mem = await get_or_create(session_id, conversation_id)
    budget = _budgets.setdefault(mem.conversation_id, TokenBudgetManager())

    mem.add_turn("user", user_message)
    yield _event("state", {"state": mem.state, "conversation_id": mem.conversation_id})

    if budget.exhausted:
        yield _event("error", {"message": "Presupuesto de tokens agotado. Inicia una nueva consulta."})
        return

    # ── GREETING ──────────────────────────────────────────────────────────
    if mem.state == ConversationState.GREETING:
        greeting = (
            "¡Hola! Soy tu asistente de salud. Estoy aquí para ayudarte a conocer "
            "cuánto pagarás por tu consulta médica *antes* de ir.\n\n"
            "Por favor, **describe con tus propias palabras** qué síntoma o malestar "
            "tienes. No te preocupes si no sabes el nombre médico — cuéntame como si "
            "le explicaras a un familiar."
        )
        mem.add_turn("assistant", greeting)
        mem.state = ConversationState.SYMPTOM_COLLECTION
        yield _event("message", {"role": "assistant", "content": greeting})
        yield _event("token_budget", budget.summary())
        await mem.persist()
        return

    # ── SYMPTOM_COLLECTION ────────────────────────────────────────────────
    if mem.state == ConversationState.SYMPTOM_COLLECTION:
        yield _event("thinking", {"agent": "A1", "message": "Analizando tus síntomas..."})
        r1 = await _a1.run(user_message, mem)
        budget.consume(r1.input_tokens + r1.output_tokens)
        if not r1.success:
            yield _event("error", {"message": "No pude entender el síntoma. ¿Puedes describirlo de otra forma?"})
            return

        mem.patient_context["sintoma_principal"] = r1.data.get("sintoma_principal", user_message)
        mem.patient_context["a1_result"] = r1.data
        mem.state = ConversationState.SPECIALTY_SUGGESTION

        # ── A2 ‖ A3 en paralelo ────────────────────────────────────────
        yield _event("thinking", {"agent": "A2+A3", "message": "Identificando especialidad y buscando tu póliza..."})
        r2, r3 = await asyncio.gather(
            _a2.run(r1.data, mem),
            _a3.run(mem),
        )
        budget.consume(r2.input_tokens + r2.output_tokens + r3.input_tokens + r3.output_tokens)

        if r2.success:
            mem.patient_context["especialidad"] = r2.data.get("especialidad_primaria", "")
            mem.patient_context["a2_result"] = r2.data

        if r3.success and r3.data:
            mem.patient_context["poliza"] = r3.data

        urgencia = r2.data.get("urgencia", "NORMAL") if r2.success else "NORMAL"
        especialidad = mem.patient_context.get("especialidad", "Medicina General")

        reply_parts = [
            f"Basado en lo que describes, parece que necesitas atención de **{especialidad}**.",
        ]
        if urgencia == "EMERGENCIA":
            reply_parts.append("⚠️ **Urgencia ALTA** — te recomiendo ir a urgencias hoy mismo.")
        elif urgencia == "URGENTE":
            reply_parts.append("⏰ Te recomiendo consultar en los próximos 1-2 días.")
        else:
            reply_parts.append("📅 Puedes programar una cita esta semana.")

        if "poliza" not in mem.patient_context:
            reply_parts.append(
                "\n¿Tienes a mano tu **número de póliza de seguro médico**? "
                "Lo necesito para calcular exactamente cuánto pagarás. "
                "(Si no tienes póliza, te mostraré precios de referencia.)"
            )
            mem.state = ConversationState.POLICY_LOOKUP
        else:
            reply_parts.append("\n✅ Encontré tu póliza. Calculando tu copago...")
            mem.state = ConversationState.COPAY_CALCULATION

        reply = "\n".join(reply_parts)
        mem.add_turn("assistant", reply)
        mem.total_tokens = budget._used
        yield _event("specialty", r2.data if r2.success else {})
        yield _event("message", {"role": "assistant", "content": reply})
        yield _event("token_budget", budget.summary())
        await mem.persist()
        return

    # ── POLICY_LOOKUP ─────────────────────────────────────────────────────
    if mem.state == ConversationState.POLICY_LOOKUP:
        mem.patient_context["numero_poliza"] = user_message.strip()
        yield _event("thinking", {"agent": "A3", "message": "Consultando tu póliza..."})
        r3 = await _a3.run(mem)
        budget.consume(r3.input_tokens + r3.output_tokens)

        if r3.success and r3.data:
            mem.patient_context["poliza"] = r3.data
            plan = r3.data.get("plan_nombre", "tu plan")
            reply = f"✅ Encontré tu póliza **{plan}**. Calculando tu copago exacto..."
        else:
            mem.patient_context["poliza"] = {
                "plan_nombre": "Plan Demo",
                "copago_pct": 20,
                "deducible_anual": 500,
                "deducible_consumido": 0,
                "cobertura_consulta_externa": True,
                "cobertura_especialistas": True,
                "cobertura_emergencias": True,
                "coaseguro_pct": 0,
                "red_hospitales_autorizados": [],
            }
            reply = "ℹ️ No encontré tu póliza en el sistema. Usaré valores de referencia del mercado ecuatoriano."

        mem.add_turn("assistant", reply)
        mem.state = ConversationState.COPAY_CALCULATION
        yield _event("message", {"role": "assistant", "content": reply})

    # ── COPAY_CALCULATION ─────────────────────────────────────────────────
    if mem.state == ConversationState.COPAY_CALCULATION:
        yield _event("thinking", {"agent": "A4+A5", "message": "Calculando copago y buscando hospitales..."})
        r4, r5 = await asyncio.gather(
            _a4.run(mem),
            _a5.run(mem),
        )
        budget.consume(r4.input_tokens + r4.output_tokens + r5.input_tokens + r5.output_tokens)

        # ── A8 — Validación determinista del copago (guardrail no-LLM) ────
        if r4.success and r4.data:
            yield _event("thinking", {"agent": "A8", "message": "Verificando el cálculo del copago..."})
            validation = validate_copay(
                r4.data,
                mem.patient_context.get("poliza", {}),
                mem.patient_context.get("especialidad", ""),
            )
            if validation.discrepancia:
                # El valor determinista —verificable y reproducible— es el autoritativo
                r4.data["copago_estimado_usd"] = validation.copago_autoritativo_usd
                r4.data.setdefault("advertencias", []).extend(validation.notas)
                try:
                    from services import audit_service
                    await audit_service.log_event(
                        session_hash=make_session_hash(session_id),
                        event_type=audit_service.AuditEvent.AGENT_INVOKED,
                        resource="copay_validator",
                        resource_id=mem.conversation_id,
                        details={
                            "discrepancia_pct": validation.variacion_pct,
                            "copago_modelo_usd": validation.copago_modelo_usd,
                            "copago_verificado_usd": validation.copago_determinista_usd,
                        },
                    )
                except Exception:
                    pass
            r4.data["validacion"] = validation.to_dict()
            mem.patient_context["copago"] = r4.data

            # ── A9 — Predicción del costo del episodio completo ───────────
            yield _event("thinking", {"agent": "A9", "message": "Proyectando el costo del episodio completo..."})
            episode = predict_episode(
                mem.patient_context.get("poliza", {}),
                mem.patient_context.get("especialidad", ""),
                costo_consulta_real=r4.data.get("costo_consulta_usd"),
            )
            r4.data["episodio"] = episode.to_dict()
            mem.patient_context["episodio"] = episode.to_dict()
            await save_episode_prediction(
                make_session_hash(session_id), mem.conversation_id, episode
            )
            yield _event("episode_forecast", episode.to_dict())

        if r5.success:
            mem.patient_context["hospitales"] = r5.data.get("hospitales", [])

        if r4.data:
            yield _event("copay", r4.data)
            if "validacion" in r4.data:
                yield _event("validation", r4.data["validacion"])
        if r5.data:
            yield _event("hospitals", r5.data)

        yield _event("thinking", {"agent": "A6", "message": "Preparando tu resumen personalizado..."})
        r6 = await _a6.run(mem)
        budget.consume(r6.input_tokens + r6.output_tokens)

        summary_text = r6.raw_text if r6.success else "Tu estimado está listo. Revisa los datos arriba."
        mem.add_turn("assistant", summary_text)
        mem.state = ConversationState.SUMMARY
        mem.total_tokens = budget._used
        yield _event("message", {"role": "assistant", "content": summary_text})
        yield _event("token_budget", budget.summary())
        yield _event("completed", {"conversation_id": mem.conversation_id})
        await mem.persist()
        return

    # ── SUMMARY / COMPLETED — allow follow-up questions ──────────────────
    if mem.state in (ConversationState.SUMMARY, ConversationState.COMPLETED):
        followup = (
            f"Entendido. Tu copago estimado para **{mem.patient_context.get('especialidad', 'la consulta')}** "
            f"ya está calculado. ¿Hay algo más en lo que pueda ayudarte? "
            "Puedes preguntarme sobre hospitales específicos, el deducible, o iniciar una nueva consulta."
        )
        mem.add_turn("assistant", followup)
        await mem.persist()
        yield _event("message", {"role": "assistant", "content": followup})
        yield _event("token_budget", budget.summary())
