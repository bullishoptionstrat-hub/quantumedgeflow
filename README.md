# Quantum Edge Flow

<div align="center">

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-C06524)](https://github.com/bullishoptionstrat-hub/quantumedgeflow/blob/main/LICENSE)
[![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C?logo=cplusplus)](https://isocpp.org/)
[![Qt6](https://img.shields.io/badge/Qt-6-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

[![GitHub Stars](https://img.shields.io/github/stars/bullishoptionstrat-hub/quantumedgeflow?style=social)](https://github.com/bullishoptionstrat-hub/quantumedgeflow/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/bullishoptionstrat-hub/quantumedgeflow?style=social)](https://github.com/bullishoptionstrat-hub/quantumedgeflow/network/members)
[![GitHub Release](https://img.shields.io/github/v/release/bullishoptionstrat-hub/quantumedgeflow?color=brightgreen&logo=github)](https://github.com/bullishoptionstrat-hub/quantumedgeflow/releases)
[![GitHub Issues](https://img.shields.io/github/issues/bullishoptionstrat-hub/quantumedgeflow)](https://github.com/bullishoptionstrat-hub/quantumedgeflow/issues)

### **Your Thinking is the Only Limit. The Data Isn't.**

State-of-the-art financial intelligence platform with CFA-level analytics, AI automation, and unlimited data connectivity.

[📥 Download](https://github.com/bullishoptionstrat-hub/quantumedgeflow/releases) · [📚 Docs](https://github.com/bullishoptionstrat-hub/quantumedgeflow/tree/main/docs) · [💬 Discussions](https://github.com/bullishoptionstrat-hub/quantumedgeflow/discussions) · [🤝 Partner](https://github.com/bullishoptionstrat-hub/quantumedgeflow/blob/main/docs/COMMERCIAL_LICENSE.md)

</div>

---

## About

**Quantum Edge Flow v4** is a pure native C++20 desktop application. It uses **Qt6** for UI and rendering, embedded **Python** for analytics, and delivers Bloomberg-terminal-class performance in a single native binary.

---

## Features

| **Feature** | **Description** |
|-------------|-----------------|
| 📊 **CFA-Level Analytics** | DCF models, portfolio optimization, risk metrics (VaR, Sharpe), derivatives pricing via embedded Python |
| 🤖 **AI Agents** | 37 agents across Trader/Investor (Buffett, Graham, Lynch, Munger, Klarman, Marks…), Economic, and Geopolitics frameworks; local LLM support; multi-provider (OpenAI, Anthropic, Gemini, Groq, DeepSeek, MiniMax, OpenRouter, Ollama) |
| 🌐 **100+ Data Connectors** | DBnomics, Polygon, Kraken, Yahoo Finance, FRED, IMF, World Bank, AkShare, government APIs, plus optional alternative-data overlays |
| 📈 **Real-Time Trading** | Crypto (Kraken/HyperLiquid WebSocket), equity, algo trading, paper trading engine, 16 broker integrations (Zerodha, Angel One, Upstox, Fyers, Dhan, Groww, Kotak, IIFL, 5paisa, AliceBlue, Shoonya, Motilal, IBKR, Alpaca, Tradier, Saxo) |
| 🔬 **QuantLib Suite** | 18 quantitative analysis modules — pricing, risk, stochastic, volatility, fixed income |
| 🚢 **Global Intelligence** | Maritime tracking, geopolitical analysis, relationship mapping, satellite data |
| 🎨 **Visual Workflows** | Node editor for automation pipelines, MCP tool integration |
| 🧠 **AI Quant Lab** | ML models, factor discovery, HFT, reinforcement learning trading |

---

## Installation

<!-- DOWNLOAD-TABLE-START -->
### Option 1 — Download Installer (Recommended)

Latest release: **v4.0.3** — [View all releases](https://github.com/bullishoptionstrat-hub/quantumedgeflow/releases/tag/v4.0.3)

| Platform | Download | Run |
|----------|----------|-----|
| **Windows x64** | [QuantumEdgeFlow-Windows-x64-setup.exe](https://github.com/bullishoptionstrat-hub/quantumedgeflow/releases/download/v4.0.3/QuantumEdgeFlow-4.0.3-windows-x64-setup.exe) | Run installer → launch `QuantumEdgeFlow.exe` |
| **Linux x64** | [QuantumEdgeFlow-Linux-x64.run](https://github.com/bullishoptionstrat-hub/quantumedgeflow/releases/download/v4.0.3/QuantumEdgeFlow-4.0.3-linux-x64-setup.run) | `chmod +x` → run installer |
| **macOS Apple Silicon** | [QuantumEdgeFlow-macOS-arm64.dmg](https://github.com/bullishoptionstrat-hub/quantumedgeflow/releases/download/v4.0.3/QuantumEdgeFlow-4.0.3-macos-arm64-setup.dmg) | Open DMG → drag to Applications |
<!-- DOWNLOAD-TABLE-END -->

---

### Option 2 — Quick Start (One-Click Build)

```bash
# Linux / macOS
git clone https://github.com/bullishoptionstrat-hub/quantumedgeflow.git
cd quantumedgeflow
chmod +x setup.sh && ./setup.sh
```

> **Windows:** Use the manual build steps in Option 4 below.

---

### Option 3 — Docker (CI / Developer Environments)

> Docker is for CI/testing only. Use Option 1 for the best experience. Requires Linux + X11.

```bash
git clone https://github.com/bullishoptionstrat-hub/quantumedgeflow.git
cd quantumedgeflow
docker build -t quantum-edge-flow .
docker run --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix quantum-edge-flow
```

---

### Option 4 — Build from Source (Manual)

> **Versions are pinned.** Use the exact versions below.

#### Prerequisites

| Tool | Pinned Version | Notes |
|------|----------------|-------|
| **Git** | latest | — |
| **CMake** | **3.27.7** | [Download](https://cmake.org/download/) |
| **Ninja** | **1.11.1** | [Download](https://github.com/ninja-build/ninja/releases) |
| **C++ compiler** | **MSVC 19.38** (VS 2022 17.8) / **GCC 12.3** / **Apple Clang 15.0** | C++20 required |
| **Qt** | **6.8.3** | [Qt Online Installer](https://www.qt.io/download-qt-installer) |
| **Python** | **3.11.9** | [python.org](https://www.python.org/downloads/release/python-3119/) |

#### Build (CMake presets)

```bash
git clone https://github.com/bullishoptionstrat-hub/quantumedgeflow.git
cd quantumedgeflow/fincept-qt
```

```powershell
cmake --preset win-release      # Windows
cmake --preset linux-release    # Linux
cmake --preset macos-release    # macOS
```

```powershell
cmake --build --preset win-release      # Windows
cmake --build --preset linux-release    # Linux
cmake --build --preset macos-release    # macOS
```

#### Run

```bash
./build/<preset>/QuantumEdgeFlow         # Linux / macOS
.\build\<preset>\QuantumEdgeFlow.exe     # Windows
```

#### Troubleshooting

1. **"Could not find Qt6 6.8.3"** — verify `CMAKE_PREFIX_PATH` points to Qt 6.8.3.
2. **MSVC version error** — use VS 2022 17.8+ (MSVC 19.38+). Check with `cl /?`.
3. Clean rebuild: delete `build/<preset>/` and re-run configure.

---

## What Sets Us Apart

**Quantum Edge Flow** is an open-source financial platform built for those who refuse to be limited by traditional software. We compete on **analytics depth** and **data accessibility**.

- **Native performance** — C++20 with Qt6, no Electron/web overhead
- **Single binary** — no Node.js, no browser runtime, no JavaScript bundler
- **CFA-level analytics** — complete curriculum coverage via Python modules
- **100+ data connectors** — from Yahoo Finance to government databases
- **Free & Open Source** (AGPL-3.0) with commercial licenses available

---

## Roadmap

| Timeline | Milestone |
|----------|-----------|
| **Shipped** | Real-time streaming, 16 broker integrations, multi-account trading, PIN authentication, theme system |
| **Q2 2026** | Options strategy builder, multi-portfolio management, 50+ AI agents |
| **Q3 2026** | Programmatic API, ML training UI, institutional features |
| **Future** | Mobile companion, cloud sync, community marketplace |

---

## Contributing

- [Contributing Guide](docs/CONTRIBUTING.md)
- [C++ Contributing Guide](fincept-qt/CONTRIBUTING.md)
- [Report Bug](https://github.com/bullishoptionstrat-hub/quantumedgeflow/issues)
- [Request Feature](https://github.com/bullishoptionstrat-hub/quantumedgeflow/discussions)

---

## License

**Dual Licensed: AGPL-3.0 (Open Source) + Commercial**

### Open Source (AGPL-3.0)
- Free for personal, educational, and non-commercial use
- Requires sharing modifications when distributed or used as network service

### Commercial License
- Required for business use
- Details: [Commercial License Guide](https://github.com/bullishoptionstrat-hub/quantumedgeflow/blob/main/docs/COMMERCIAL_LICENSE.md)

### Trademarks
"Quantum Edge Flow" is a trademark of Quantum Edge Flow / Quantum Edge Capital LLC.

© 2025-2026 Quantum Edge Flow. All rights reserved.

---

<div align="center">

### **Your Thinking is the Only Limit. The Data Isn't.**

⭐ **Star** · 🔄 **Share** · 🤝 **Contribute**

</div>
