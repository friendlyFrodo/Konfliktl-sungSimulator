#!/usr/bin/env python3
"""Test-Simulation des Konflikt-Simulators mit Mediator-Rolle."""

import asyncio
import json
import websockets
from datetime import datetime

# Conversation log for final output
conversation_log = []
evaluation_result = None

async def test_mediator_simulation():
    """Simuliert einen Gesprächsverlauf mit Mediator-Eingriffen."""
    global conversation_log, evaluation_result

    uri = "ws://localhost:8080/ws"
    session_id = None

    async with websockets.connect(uri) as ws:
        print("=" * 60)
        print("KONFLIKT-SIMULATOR TEST - Mediator-Modus")
        print("=" * 60)
        print()

        # 1. Session starten
        start_msg = {
            "type": "start_session",
            "mode": "mediator",
            "agent_a_config": {
                "name": "Lisa",
                "prompt": """Du bist Lisa, 34 Jahre alt. Du bist emotional, fühlst dich oft ungerecht behandelt.

WICHTIGE VERHALTENSREGELN:
- Du reagierst emotional auf Kritik
- Du verwendest oft "Du machst immer..." Formulierungen
- Unter der Oberfläche fühlst du dich unsicher

SZENARIO: Es geht um die Urlaubsplanung. Thomas hat ohne dich zu fragen bereits einen Wanderurlaub gebucht, obwohl du lieber ans Meer wolltest.

WICHTIG: Antworte NUR als Lisa. Beschreibe Gestik in der dritten Person (*Lisa verschränkt die Arme*)."""
            },
            "agent_b_config": {
                "name": "Thomas",
                "prompt": """Du bist Thomas, 36 Jahre alt. Du bist rational und analytisch.

WICHTIGE VERHALTENSREGELN:
- Du bleibst oberflächlich ruhig, wirst aber sarkastisch wenn frustriert
- Du versuchst Probleme zu "lösen" statt Gefühle zu validieren
- Du verwendest Fakten und Logik als Abwehr

SZENARIO: Du hast einen Wanderurlaub gebucht, weil er günstiger war und du dachtest, Lisa würde sich anpassen. Du verstehst ihre Aufregung nicht.

WICHTIG: Antworte NUR als Thomas. Beschreibe Gestik in der dritten Person (*Thomas seufzt*)."""
            },
            "scenario": "Streit über Urlaubsplanung - Thomas hat ohne Absprache gebucht"
        }

        await ws.send(json.dumps(start_msg))
        print("[SYSTEM] Session wird gestartet...\n")

        # Nachrichten empfangen bis waiting_for_decision
        current_speaker = None
        current_content = ""

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "session_started":
                session_id = msg["session_id"]
                print(f"[SYSTEM] Session ID: {session_id[:8]}...\n")

            elif msg_type == "typing":
                current_speaker = msg["agent_name"]
                current_content = ""
                print(f"[{current_speaker} tippt...]")

            elif msg_type == "streaming_chunk":
                current_content += msg["chunk"]

            elif msg_type == "agent_message":
                agent_name = msg["agent_name"]
                content = msg["content"]
                conversation_log.append({"speaker": agent_name, "content": content})
                print(f"\n{agent_name}: {content}\n")
                print("-" * 40)

            elif msg_type == "waiting_for_decision":
                print(f"\n[SYSTEM] Warte auf Entscheidung...")
                break

            elif msg_type == "error":
                print(f"[FEHLER] {msg['message']}")
                return

        # --- RUNDE 2: Continue - Thomas antwortet ---
        print("\n[MEDIATOR] Lasse Thomas antworten...\n")
        await ws.send(json.dumps({"type": "continue", "session_id": session_id}))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # --- RUNDE 3: Mediator greift ein ---
        mediator_msg_1 = """*Der Mediator hebt die Hand*

Einen Moment bitte. Lisa, ich höre, dass Sie sich übergangen fühlen. Thomas, Sie haben aus praktischen Gründen gehandelt.

Lassen Sie mich zusammenfassen: Es geht hier nicht nur um den Urlaub selbst, sondern um das Gefühl, bei wichtigen Entscheidungen einbezogen zu werden. Lisa, habe ich das richtig verstanden?"""

        print(f"\n[MEDIATOR GREIFT EIN]\n")
        conversation_log.append({"speaker": "Mediator", "content": mediator_msg_1})
        print(f"Mediator: {mediator_msg_1}\n")
        print("-" * 40)

        await ws.send(json.dumps({
            "type": "user_message",
            "session_id": session_id,
            "content": mediator_msg_1,
            "role": "mediator"
        }))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # --- RUNDE 4: Continue - Thomas reagiert ---
        print("\n[MEDIATOR] Lasse Thomas reagieren...\n")
        await ws.send(json.dumps({"type": "continue", "session_id": session_id}))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # --- RUNDE 5: Mediator versucht Interessen herauszuarbeiten ---
        mediator_msg_2 = """Thomas, Sie haben gerade gesagt, dass Sie praktische Gründe hatten. Können Sie mir mehr darüber erzählen, was Ihnen bei einem Urlaub wichtig ist? Was erhoffen Sie sich davon?"""

        print(f"\n[MEDIATOR]\n")
        conversation_log.append({"speaker": "Mediator", "content": mediator_msg_2})
        print(f"Mediator: {mediator_msg_2}\n")
        print("-" * 40)

        await ws.send(json.dumps({
            "type": "user_message",
            "session_id": session_id,
            "content": mediator_msg_2,
            "role": "mediator"
        }))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # --- RUNDE 6: Lisa soll auch zu Wort kommen ---
        print("\n[MEDIATOR] Lasse Lisa reagieren...\n")
        await ws.send(json.dumps({"type": "continue", "session_id": session_id}))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # --- RUNDE 7: Mediator macht einen Fehler (für die Evaluierung interessant) ---
        mediator_msg_3 = """Lisa, ich verstehe Sie vollkommen. Thomas hätte wirklich vorher fragen sollen - das war nicht fair von ihm.

Thomas, sehen Sie nicht, wie verletzend das für Lisa war?"""

        print(f"\n[MEDIATOR - mit problematischer Intervention]\n")
        conversation_log.append({"speaker": "Mediator", "content": mediator_msg_3})
        print(f"Mediator: {mediator_msg_3}\n")
        print("-" * 40)

        await ws.send(json.dumps({
            "type": "user_message",
            "session_id": session_id,
            "content": mediator_msg_3,
            "role": "mediator"
        }))

        # Lisa reagiert auf die parteiliche Äußerung
        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # Thomas soll auch noch reagieren
        print("\n[MEDIATOR] Lasse Thomas reagieren...\n")
        await ws.send(json.dumps({"type": "continue", "session_id": session_id}))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[{msg['agent_name']} tippt...]")
            elif msg_type == "agent_message":
                conversation_log.append({"speaker": msg["agent_name"], "content": msg["content"]})
                print(f"\n{msg['agent_name']}: {msg['content']}\n")
                print("-" * 40)
            elif msg_type == "waiting_for_decision":
                break

        # --- EVALUIERUNG ANFORDERN ---
        print("\n" + "=" * 60)
        print("EVALUIERUNG WIRD ANGEFORDERT...")
        print("=" * 60 + "\n")

        await ws.send(json.dumps({
            "type": "request_evaluation",
            "session_id": session_id
        }))

        while True:
            msg = json.loads(await ws.recv())
            msg_type = msg.get("type")

            if msg_type == "typing":
                print(f"[Coach analysiert...]")
            elif msg_type == "streaming_chunk":
                pass  # Ignore streaming for cleaner output
            elif msg_type == "evaluation":
                evaluation_result = msg["content"]
                print("\n" + "=" * 60)
                print("COACH-EVALUIERUNG")
                print("=" * 60)
                print(evaluation_result)
                break
            elif msg_type == "error":
                print(f"[FEHLER] {msg['message']}")
                break

    # Final summary
    print("\n\n")
    print("=" * 60)
    print("VOLLSTÄNDIGER GESPRÄCHSVERLAUF")
    print("=" * 60)
    for entry in conversation_log:
        print(f"\n[{entry['speaker']}]: {entry['content']}")

    print("\n\n")
    print("=" * 60)
    print("COACH-ANALYSE")
    print("=" * 60)
    if evaluation_result:
        print(evaluation_result)


if __name__ == "__main__":
    asyncio.run(test_mediator_simulation())
