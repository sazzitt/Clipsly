# Authentication & Security Architecture

**Project Name:** AI Video Clipper (Working Title: Clipsly)  
**Document Version:** 0.1.0  
**Status:** PLANNED (To be detailed in Phase 02 / implemented in Phase 04)  
**Author:** Security Architect & Systems Engineer  

---

## 1. Purpose of this Document

This document defines the security posture, threat model, data privacy boundaries, and defensive programming practices for the AI Video Clipper application.

Even though this is a single-user, local-first application with no public cloud accounts or payment processing, running local web servers and invoking system-level media tools (such as FFmpeg) introduces specific security vectors—including path traversal, command injection, and unintended local network exposure—that require rigorous mitigation.

---

## 2. Security Threat Model & Defense Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                 Threat Model & Mitigations                  │
├──────────────────────────────┬──────────────────────────────┤
│ Potential Threat Vector      │ Engineered Mitigation        │
├──────────────────────────────┼──────────────────────────────┤
│ Path Traversal (Arbitrary    │ Strict UUID filename mapping │
│ File Overwrite / Read)       │ and regex path sanitization  │
├──────────────────────────────┼──────────────────────────────┤
│ Command Injection via FFmpeg │ Parameterized argument lists;│
│ / Subprocess Execution       │ strictly no `shell=True`     │
├──────────────────────────────┼──────────────────────────────┤
│ Unauthorized Local Network   │ Explicit loopback binding    │
│ Access (LAN devices)         │ to `127.0.0.1` (never 0.0.0.0)│
├──────────────────────────────┼──────────────────────────────┤
│ Cross-Origin Request Abuse   │ Strict CORS origins locked to│
│ (Malicious browser tabs)     │ localhost ports              │
├──────────────────────────────┼──────────────────────────────┤
│ Media / Data Exfiltration    │ Air-gapped zero telemetry;   │
│                              │ no outbound analytics calls  │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Core Defensive Controls

### 3.1 Network Binding & Loopback Isolation
The FastAPI backend server and Vite development server bind exclusively to `127.0.0.1` (loopback). Binding to `0.0.0.0` is strictly prohibited, ensuring other devices on the same Wi-Fi/LAN network cannot access the video studio or view uploaded media.

### 3.2 Path Traversal & File Upload Sanitization
When a user uploads a video:
1. The original filename is stripped of all directory separators (`/`, `\`), control characters, and non-ASCII glyphs using regex `re.sub(r'[^a-zA-Z0-9_\-\.]', '', raw_filename)`.
2. A cryptographically random UUIDv4 is prepended to ensure uniqueness (e.g., `a7c1b82e-9d04-4f2b-8a5f_my_podcast.mp4`).
3. Files are stored strictly within the validated `/storage/uploads/` directory; attempts to pass `../` trigger immediate 400 Bad Request responses.

### 3.3 Subprocess Command Injection Prevention
When invoking FFmpeg or FFprobe:
- Commands are passed strictly as structured argument arrays: `['ffmpeg', '-i', str(input_path), ...]`.
- Use of `shell=True` in Python `subprocess` or `asyncio.subprocess` is **strictly forbidden**, eliminating shell escape and injection exploits.

### 3.4 Single-User Scope & Authentication Policy
Because this is a personal desktop application operating on a secure local laptop:
- User authentication (passwords, JWTs, OAuth) is explicitly **out of scope**.
- Adding login barriers to a local tool adds friction without meaningful security value.
- Security relies on OS-level user account isolation.

---

## 4. Planned Sections for Phase 04 Specification

During Phase 04, this document will be expanded to include:
- Complete CORS middleware configuration for FastAPI.
- File integrity hash checking (SHA-256) for uploaded and exported media.
- Subprocess execution wrapper source implementation (`SafeSubprocessRunner`).

---

## 5. Current Status & Next Steps

- **Status:** PLANNED.
- **Immediate Dependency:** System Architecture (Phase 02).
- **Execution Target:** Phase 04.
