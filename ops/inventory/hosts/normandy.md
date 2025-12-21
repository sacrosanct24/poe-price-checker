# NORMANDY - Machine Specifications

## Operational Notes
- Primary role: headless worker / LLM inference node.
- Access: SSH (22) and Ollama API (11434) on the local network; RDP (3389) when needed.
- Do not expose SSH, Ollama, or RDP to the public internet.

**Purpose:** Headless LLM Inference Server
**Renamed From:** DESKTOP-KNOUDN5
**Date:** December 20, 2025

---

## System Overview

| Component | Specification |
|-----------|---------------|
| **Hostname** | Normandy |
| **IP Address** | 192.168.87.127 |
| **OS** | Windows 11 Pro (Build 26200) |
| **Architecture** | x64-based PC |
| **Manufacturer** | ASUS |

---

## Processor (CPU)

| Specification | Value |
|---------------|-------|
| **Model** | Intel Core i9-10900 |
| **Architecture** | Comet Lake (10th Gen) |
| **Cores / Threads** | 10 / 20 |
| **Base Clock** | 2.80 GHz |
| **Turbo Clock** | 5.20 GHz |
| **TDP** | 65W (125W Turbo) |
| **Socket** | LGA 1200 |

---

## Memory (RAM)

| Specification | Value |
|---------------|-------|
| **Total** | 128 GB |
| **Type** | DDR4-2666 |
| **Configuration** | 4x 32GB |
| **Manufacturer** | G.Skill |
| **Channels** | Dual Channel |

---

## Graphics (GPU)

| Specification | Value |
|---------------|-------|
| **Model** | NVIDIA GeForce RTX 4070 Ti |
| **VRAM** | 12 GB GDDR6X |
| **Architecture** | Ada Lovelace (AD104) |
| **CUDA Cores** | 7680 |
| **Max Clock** | 3135 MHz |
| **Power Limit** | 285W |
| **Driver** | 591.44 |
| **Idle Temp** | 47C |
| **Idle Power** | ~18W |

---

## Storage

| Drive | Model | Capacity | Type |
|-------|-------|----------|------|
| C: | Sabrent Rocket Q | 2 TB | NVMe SSD |
| D: (Games) | WDC WD4005FZBX | 4 TB | HDD 7200RPM |
| E: (Media) | WDC WD4005FZBX | 4 TB | HDD 7200RPM |
| F: (SSD) | CT2000MX500SSD1 | 2 TB | SATA SSD |
| H: (Backup) | Seagate Backup+ Desk | 4 TB | External USB |
| M: (M2) | Sabrent | 2 TB | NVMe SSD |

**Total Storage:** ~18 TB

---

## Motherboard

| Specification | Value |
|---------------|-------|
| **Model** | ASUS ROG STRIX Z490-E GAMING |
| **Chipset** | Intel Z490 |
| **Socket** | LGA 1200 |
| **Form Factor** | ATX |
| **BIOS** | AMI 0607 (May 2020) |

---

## Networking

| Interface | Model | Speed |
|-----------|-------|-------|
| **Ethernet** | Intel I225-V | 2.5 Gbps |
| **WiFi** | Intel AX201 | WiFi 6 (160MHz) |
| **Bluetooth** | Integrated | 5.0 |
| **VPN** | NordVPN TAP Adapter | - |

**Ethernet MAC:** D4:5D:64:D3:54:42
**WiFi MAC:** 04:33:C2:65:5F:18

---

## LLM Performance Capabilities

### Installed Models (Ollama)

| Model | Size | Parameters | Use Case | Speed (tok/s) |
|-------|------|------------|----------|---------------|
| qwen2.5-coder:7b | 4.7 GB | 7B | Code generation | ~92 |
| qwen3:8b | 5.2 GB | 8B | Reasoning (thinking mode) | ~29 |
| deepseek-r1:8b | 5.2 GB | 8B | Reasoning specialist | ~9 |
| mistral-nemo | 7.1 GB | 12B | General purpose | ~10 |
| gemma3:12b | 8.1 GB | 12B | General (Google latest) | ~16 |
| phi4 | 9.1 GB | 14B | Microsoft reasoning | ~8 |
| devstral | 14 GB | 24B | Coding agent | ~4 (offload) |
| deepseek-r1:70b | 42 GB | 70B | Max capability | ~2-5 (offload) |

**Total Model Storage:** ~96 GB
**Model Count:** 8

### Recommended Usage

| Task | Primary Model | Fallback |
|------|---------------|----------|
| **Quick coding** | qwen2.5-coder:7b | qwen3:8b |
| **Reasoning/analysis** | qwen3:8b | phi4 |
| **General chat** | gemma3:12b | mistral-nemo |
| **Complex problems** | deepseek-r1:70b | phi4 |

### Benchmarked Performance (December 2025)

| Metric | Value |
|--------|-------|
| **7-8B Model Throughput** | 29-92 tokens/sec |
| **12-14B Model Throughput** | 8-16 tokens/sec |
| **24B Model Throughput** | ~4 tokens/sec (CPU offload) |
| **70B Model Throughput** | ~2-5 tokens/sec (heavy offload) |
| **VRAM Available** | 12 GB |
| **RAM Available for Offload** | 128 GB |

### Performance Tiers
- **Tier 1 (Full GPU):** Models <=8B - qwen2.5-coder, qwen3, deepseek-r1:8b
- **Tier 2 (Mostly GPU):** Models 12-14B - gemma3, mistral-nemo, phi4
- **Tier 3 (GPU+Offload):** Models >14B - devstral, deepseek-r1:70b

### Strengths
- 128GB RAM allows running large models with CPU offload
- RTX 4070 Ti provides good FP16/INT8 inference
- Fast NVMe storage for model loading
- 2.5GbE networking for remote access

### Limitations
- 12GB VRAM limits full GPU inference to ~13B parameter models
- DDR4-2666 slower than DDR5 for CPU offload scenarios
- 10th gen CPU lacks AVX-512 (available in 11th gen+)

---

## Software Configuration

### Enabled Services
- Ollama (LLM inference server)
- OpenSSH Server (for remote terminal access)

### Disabled/Removed Services (December 20, 2025)

| Software | Action | RAM Saved |
|----------|--------|-----------|
| Corsair iCUE | Uninstalled | ~170 MB |
| Creative App | Uninstalled | ~295 MB |
| Logitech Options+ | Uninstalled | ~150 MB |
| Google Drive | Uninstalled | ~50 MB |
| Razer Cortex | Uninstalled | ~30 MB |
| Razer Synapse | Uninstalled | ~65 MB |
| SideQuest (VR) | Uninstalled | ~20 MB |
| Dropbox | Uninstalled | ~35 MB |
| AURA Service | Uninstalled | ~30 MB |
| AI Suite 3 | Uninstalled | ~50 MB |
| NahimicService | Disabled | ~50 MB |
| ROGLiveService | Disabled | ~35 MB |
| AsusCertService | Disabled | ~15 MB |
| LightingService | Disabled | ~20 MB |

**Estimated RAM savings:** ~1 GB+

### Still Installed (Optional Removal)

| Software | Notes |
|----------|-------|
| Logi Options+ | Re-appeared or not fully removed |
| Docker Desktop | Useful for dev, but uses resources |
| Armoury Crate | ASUS utility, difficult to remove |
| Overwolf | Game overlay platform |
| Plex Media Server | Media streaming |
| Microsoft Copilot | MSIX app |

### Active Process Count
~250 (optimized from ~342)

---

## Remote Headless Access

### Option 1: SSH Terminal Access (Recommended)

**Setup OpenSSH Server:**
```powershell
# Run as Administrator
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# Allow through firewall (usually auto-configured)
New-NetFirewallRule -Name "SSH" -DisplayName "OpenSSH Server" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

**Connect from another machine:**
```bash
ssh Todd@192.168.87.127
# or by hostname (if DNS resolves)
ssh Todd@normandy
```

---

### Option 2: Ollama API Access (For LLM Queries)

**Configure Ollama for network access:**
```powershell
# Set environment variable to listen on all interfaces
[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0', 'Machine')

# Restart Ollama service
Stop-Process -Name "ollama app" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
# Then restart Ollama from Start Menu or reboot
```

**Open firewall for Ollama:**
```powershell
New-NetFirewallRule -Name "Ollama" -DisplayName "Ollama LLM API" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 11434
```

**Test from remote machine:**
```bash
# List models
curl http://192.168.87.127:11434/api/tags

# Run inference
curl http://192.168.87.127:11434/api/generate -d '{
  "model": "qwen3:8b",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

---

### Option 3: Remote Desktop (RDP)

For occasional GUI access (not truly headless):
```powershell
# Enable Remote Desktop
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

**Connect:** Use Remote Desktop app -> `192.168.87.127` or `normandy`

---

### Network Services Summary (Verified December 20, 2025)

| Service | Port | Status | Command |
|---------|------|--------|---------|
| SSH | 22 | Running | `ssh Todd@192.168.87.127` |
| Ollama API | 11434 | Running (0.0.0.0) | `curl http://192.168.87.127:11434/api/tags` |
| RDP | 3389 | Enabled | `mstsc /v:192.168.87.127` |

**Firewall Rules:** All three services have inbound rules configured and enabled.

---

### Security Recommendations

1. **Use SSH keys** instead of passwords for SSH access
2. **Keep NordVPN active** if accessing over internet
3. **Restrict Ollama** to local network (don't expose port 11434 to internet)
4. **Disable RDP** when not needed (it's resource-heavy)

---

### Quick Reference - Remote LLM Usage

**From Falcon or other network machine:**
```python
import requests

response = requests.post('http://192.168.87.127:11434/api/generate', json={
    'model': 'qwen3:8b',
    'prompt': 'Explain quantum computing briefly',
    'stream': False
})
print(response.json()['response'])
```

**Using ollama CLI remotely (set on client machine):**
```bash
# Windows
set OLLAMA_HOST=http://192.168.87.127:11434

# Linux/Mac
export OLLAMA_HOST=http://192.168.87.127:11434

ollama list
ollama run qwen3:8b "Hello!"
```

---

*Generated: December 20, 2025*
*LLM Inventory Updated: December 20, 2025*
*Remote Access Verified: December 20, 2025*
