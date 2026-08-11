import runpod
import os
import boto3
import torch
import torchaudio
import base64
import io

from chatterbox.tts import ChatterboxTTS

# R2 Configuration
s3 = boto3.client('s3',
    endpoint_url=f"https://{os.environ.get('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ.get('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('R2_SECRET_ACCESS_KEY')
)
BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'comfy')

# Global State
MODEL = None
R2_CACHE = {}  # path -> local_path


def load_model():
    global MODEL
    print("Loading Chatterbox TTS model...")
    MODEL = ChatterboxTTS.from_pretrained(device="cuda")
    print("Model loaded.")


def _download_from_r2(r2_key, local_path):
    """Download file from R2, with local caching."""
    if r2_key in R2_CACHE and os.path.exists(R2_CACHE[r2_key]):
        return R2_CACHE[r2_key]

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    s3.download_file(BUCKET_NAME, r2_key, local_path)
    R2_CACHE[r2_key] = local_path
    return local_path


def _generate_single(text, ref_wav_path=None, exaggeration=0.5, cfg_weight=0.5):
    """Generate TTS for a single line. Returns base64-encoded WAV audio."""
    # Download ref wav from R2 if provided
    ref_local = None
    if ref_wav_path:
        safe_name = ref_wav_path.replace("/", "_")
        ref_local = f"/tmp/ref_{safe_name}"
        try:
            _download_from_r2(ref_wav_path, ref_local)
        except Exception as e:
            print(f"Warning: could not download ref wav {ref_wav_path}: {e}")
            ref_local = None

    # Generate audio
    if ref_local and os.path.exists(ref_local):
        wav = MODEL.generate(text, audio_prompt_path=ref_local,
                             exaggeration=exaggeration, cfg_weight=cfg_weight)
    else:
        wav = MODEL.generate(text, exaggeration=exaggeration, cfg_weight=cfg_weight)

    # Encode to base64 WAV
    buf = io.BytesIO()
    torchaudio.save(buf, wav, MODEL.sr, format="wav")
    return base64.b64encode(buf.getvalue()).decode()


def handler(job):
    """
    Handles both single TTS and batch TTS requests.

    Single request format:
    {
        "input": {
            "text": "Hello world",
            "voice_id": "nova",
            "ref_wav_path": "voices/nova/excited.wav",
            "exaggeration": 0.5,
            "cfg_weight": 0.5
        }
    }

    Batch request format (from pipeline s4_voice.py):
    {
        "input": {
            "action": "tts_batch",
            "lines": [
                {
                    "id": "L01",
                    "text": "WHAT IS HAPPENING?!",
                    "speaker": "Nova",
                    "ref_wav_path": "voices/nova/excited.wav"
                }
            ]
        }
    }
    """
    job_input = job.get("input", {})
    action = job_input.get("action", "tts_single")

    # ── Batch TTS (from pipeline) ───────────────────────────────────────
    if action == "tts_batch":
        lines = job_input.get("lines", [])
        if not lines:
            return {"error": "No lines provided for tts_batch."}

        results = []
        for line in lines:
            line_id = line.get("id", "unknown")
            text = line.get("text", "")
            ref_wav_path = line.get("ref_wav_path")
            exaggeration = line.get("exaggeration", 0.5)
            cfg_weight = line.get("cfg_weight", 0.5)

            if not text:
                results.append({"id": line_id, "error": "empty text"})
                continue

            try:
                audio_b64 = _generate_single(text, ref_wav_path, exaggeration, cfg_weight)
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

    # ── Single TTS ──────────────────────────────────────────────────────
    text = job_input.get("text")
    if not text:
        return {"error": "Text is required."}

    ref_wav_path = job_input.get("ref_wav_path")
    exaggeration = job_input.get("exaggeration", 0.5)
    cfg_weight = job_input.get("cfg_weight", 0.5)

    try:
        audio_b64 = _generate_single(text, ref_wav_path, exaggeration, cfg_weight)
        return {
            "audio_base64": audio_b64,
            "status": "success"
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    load_model()
    runpod.serverless.start({"handler": handler})
