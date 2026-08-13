import runpod
import os
import torch
import torchaudio
import base64
import io

from chatterbox.tts import ChatterboxTTS

# Global State
MODEL = None
REF_CACHE = {}  # hash -> local_path


def load_model():
    global MODEL
    print("Loading Chatterbox TTS model...")
    MODEL = ChatterboxTTS.from_pretrained(device="cuda")
    print("Model loaded.")


def _generate_single(text, ref_audio_base64, exaggeration=0.5, cfg_weight=0.5):
    """Generate TTS with voice cloning. ref_audio_base64 is REQUIRED."""
    # Write inline ref wav to tmp (cached by content hash)
    cache_key = hash(ref_audio_base64[:200])
    if cache_key in REF_CACHE and os.path.exists(REF_CACHE[cache_key]):
        ref_local = REF_CACHE[cache_key]
    else:
        audio_bytes = base64.b64decode(ref_audio_base64)
        ref_local = f"/tmp/ref_{cache_key}.wav"
        with open(ref_local, "wb") as f:
            f.write(audio_bytes)
        REF_CACHE[cache_key] = ref_local
        print(f"Cached ref wav: {ref_local} ({len(audio_bytes)} bytes)")

    wav = MODEL.generate(text, audio_prompt_path=ref_local,
                         exaggeration=exaggeration, cfg_weight=cfg_weight)

    buf = io.BytesIO()
    torchaudio.save(buf, wav, MODEL.sr, format="wav")
    return base64.b64encode(buf.getvalue()).decode()


def handler(job):
    """
    Voice-cloned TTS only. No ref audio = error, never default voice.

    Single:
    {
        "input": {
            "text": "Hello world",
            "ref_audio_base64": "<base64 wav>",
            "exaggeration": 0.5,
            "cfg_weight": 0.5
        }
    }

    Batch:
    {
        "input": {
            "action": "tts_batch",
            "ref_audio_base64": "<base64 wav>",
            "lines": [
                {"id": "L01", "text": "WHAT?!", "speaker": "Nova"}
            ]
        }
    }
    Note: batch ref_audio_base64 at top level = shared ref for all lines.
    Per-line ref_audio_base64 overrides batch-level ref.
    """
    job_input = job.get("input", {})
    action = job_input.get("action", "tts_single")

    # ── Batch TTS ─────────────────────────────────────────────────────
    if action == "tts_batch":
        lines = job_input.get("lines", [])
        if not lines:
            return {"error": "No lines provided for tts_batch."}

        batch_ref = job_input.get("ref_audio_base64")
        results = []

        for line in lines:
            line_id = line.get("id", "unknown")
            text = line.get("text", "")
            ref = line.get("ref_audio_base64") or batch_ref
            exaggeration = line.get("exaggeration", 0.5)
            cfg_weight = line.get("cfg_weight", 0.5)

            if not text:
                results.append({"id": line_id, "error": "empty text"})
                continue
            if not ref:
                results.append({"id": line_id, "error": "ref_audio_base64 required — no default voice"})
                continue

            try:
                audio_b64 = _generate_single(text, ref, exaggeration, cfg_weight)
                results.append({
                    "id": line_id,
                    "audio_base64": audio_b64,
                    "speaker": line.get("speaker", "unknown")
                })
                print(f"  Generated: {line_id} ({len(text)} chars)")
            except Exception as e:
                print(f"  Failed: {line_id} - {e}")
                results.append({"id": line_id, "error": str(e)})

        return {"results": results}

    # ── Single TTS ────────────────────────────────────────────────────
    text = job_input.get("text")
    if not text:
        return {"error": "text is required"}

    ref = job_input.get("ref_audio_base64")
    if not ref:
        return {"error": "ref_audio_base64 required — no default voice, won't waste credits"}

    exaggeration = job_input.get("exaggeration", 0.5)
    cfg_weight = job_input.get("cfg_weight", 0.5)

    try:
        audio_b64 = _generate_single(text, ref, exaggeration, cfg_weight)
        return {"audio_base64": audio_b64, "status": "success"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    load_model()
    runpod.serverless.start({"handler": handler})
