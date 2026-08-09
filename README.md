<div align="center">
  <img src="inumaki.png" alt="Inumaki Cursed Speech Domain" width="100%">
  <h1 align="center">cursed-speech (呪言)</h1>
  <p align="center"><i>Universal Voice Materialization Domain</i></p>
  
  [![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![RunPod](https://img.shields.io/badge/RunPod-Serverless-purple.svg?style=for-the-badge)](https://runpod.io)
</div>

---

> *"Don't move." (動くな)* — Toge Inumaki

**cursed-speech** is a universal, serverless Text-to-Speech (TTS) endpoint designed to work in perfect tandem with **[rika](https://github.com/farhann-saleem/rika-voice-clone-yt)**. 

Instead of hosting 10 different expensive GPU instances for 10 different cloned characters, `cursed-speech` runs a single base TTS model and dynamically pulls your fine-tuned voices from Cloudflare R2 on-the-fly. Zero idle costs. Infinite voices.

---

## Architecture

1. **The Core**: A heavily optimized Docker image containing the base Chatterbox TTS model. Because the 3GB base model is baked in, cold starts are incredibly fast.
2. **The Swapper**: When you request a specific voice, the handler pulls the lightweight trained weights (safetensors) from your R2 bucket and injects them into the base model instantly.
3. **The Delivery**: Generated audio is uploaded back to R2, and a pre-signed download URL is returned to your pipeline to prevent massive base64 JSON bloat.

---

## The API Payload

When the Serverless endpoint is running on RunPod, send a simple JSON request to generate audio:

```json
{
  "input": {
    "text": "HELLLLLOOOO! Did you see that?!",
    "voice_id": "nix",
    "emotion_prompting": true
  }
}
```

The endpoint will:
1. Verify if `nix` is loaded in VRAM.
2. If not, download `models/nix.safetensors` from R2.
3. Generate the TTS audio.
4. Return a fast download URL.

---

## Setup & Deployment

Read the **[SETUP.md](./SETUP.md)** file for a full guide on deploying this endpoint to RunPod via GitHub Container Registry (GHCR) and securely linking your Cloudflare R2 bucket.

<div align="center">
  <i>The mouthpiece for Rika's bound souls.</i>
</div>
