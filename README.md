<div align="center">

# 🎮 Epic Awesome Gamer
### (AiHubMix Enhanced Edition)

<img src="https://img.shields.io/static/v1?message=Python%203.12&color=3776AB&style=for-the-badge&logo=python&label=Build">
<img src="https://img.shields.io/static/v1?message=Gemini%20Pro&color=4285F4&style=for-the-badge&logo=google&label=AI%20Model">
<img src="https://img.shields.io/github/license/10000ge10000/epic-awesome-gamer?style=for-the-badge&color=orange">
<img src="https://img.shields.io/github/actions/workflow/status/10000ge10000/epic-awesome-gamer/ci.yaml?label=Auto%20Claim&style=for-the-badge&color=2ea44f">

<p class="description">
  🍷 <b>优雅、智能、全自动</b>。<br>
  专为 GitHub Actions 打造的 Epic Games Store 免费游戏领取机器人。
</p>

[特性一览](#-核心特性) • [快速部署](#-部署指南-github-actions) • [配置说明](#-配置详解-secrets) • [常见问题](#-常见问题-faq)

</div>

---

## 📖 项目简介

**Epic Awesome Gamer (AiHubMix 版)** 是一款基于 Python 的全自动 Epic 游戏领取工具。

本项目由 [**10000ge10000/epic-awesome-gamer**](https://github.com/10000ge10000/epic-awesome-gamer) 基于原作者 [**QIN2DIM/epic-awesome-gamer**](https://github.com/QIN2DIM/epic-awesome-gamer) 进行二次开发的基础上，进一步优化和修复相关bug。在此特别感谢两位作者的开源贡献与灵感！

---

## 🤔 更新与修复

本项目在 `10000ge10000/epic-awesome-gamer` 的基础上，进一步优化了 Gemini 模型接口的兼容性与稳定性，主要解决了以下问题：

*   **强化模型 ID 绑定 (Default: `gemini-2.0-flash-free`)**：
    *   **问题**：原项目中，即使在 GitHub Secrets 配置了 `GEMINI_MODEL` 环境变量，底层 `hcaptcha-challenger` 库内部可能仍使用硬编码的旧模型 ID（如 `gemini-2.5-pro` 或 `gemini-2.5-flash`），导致 `403` 或 `404` 错误。
    *   **修复**：通过修改 `settings.py`，所有在 hCaptcha 挑战中涉及的细分 AI 模型参数（`CHALLENGE_CLASSIFIER_MODEL`, `IMAGE_CLASSIFIER_MODEL`, `SPATIAL_POINT_REASONER_MODEL`, `SPATIAL_PATH_REASONER_MODEL`）现在都强制读取 `GEMINI_MODEL` 环境变量的设定。如果未设置 `GEMINI_MODEL`，**默认值已调整为 `gemini-2.0-flash-free`**，确保能正确调用一个可用的免费模型。
*   **多图分辨率兼容性修复**：
    *   **问题**：一些 Gemini 模型（特别是 `flash` 系列）在处理包含多张图片（如 hCaptcha 的九宫格挑战）的请求时，如果同时请求 `HIGH` 媒体分辨率，会返回 `400 Bad Request` 错误。
    *   **修复**：在 AI 请求发送前，自动检测并移除 `media_resolution="HIGH"` 参数，让 Gemini API 自动选择最兼容的分辨率进行处理。这彻底解决了多图验证码识别中的 400 报错。
*   **提升操作加载容错性**：
    *   调整了默认的 `EXECUTION_TIMEOUT` 和 `RESPONSE_TIMEOUT`，以适应 GitHub Actions 环境下可能存在的网络延迟和页面加载缓慢，减少因短暂等待超时导致的任务失败。

---

## ✨ 核心特性

| 模块 | 功能描述 |
| :--- | :--- |
| **🤖 AI 强力驱动** | 内置针对 `google-genai` SDK 的底层补丁，适配 **AiHubMix** 等中转站，支持 Base64 图片直传，**0 报错**通过 hCaptcha 验证。 |
| **⚡️ 即时结账支持** | 独家支持 **Instant Checkout** 流程。自动识别点击 "Get" 后弹出的支付窗口，不再因为找不到购物车而漏领。 |
| **🛡️ 智能弹窗处理** | 自动识别并处理 **"内容警告 (Content Warning)"** 和年龄限制弹窗，确保脚本不会卡在确认页面。 |
| **📦 全内容收集** | 移除了原版的捆绑包过滤逻辑，无论是普通游戏还是 **Bundles**，所有免费内容一网打尽。 |
| **☁️ 云端自动运行** | 深度适配 GitHub Actions，利用 `uv` 极速管理依赖，每周定时自动执行，零成本守护游戏库。 |

---

## 🚀 部署指南 (GitHub Actions)

这是最推荐的部署方式，完全免费，配置一次即可永久自动运行。

### 1. Fork 仓库
点击页面右上角的 **Fork** 按钮，将本项目克隆到你自己的 GitHub 账号下。

### 2. 配置 Secrets
进入你 Fork 后的仓库，依次点击：
`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

添加以下必要变量：

 变量名 | 示例 | 说明 | 
 :--- | :---: | :--- |
 `EPIC_EMAIL` | `myname@email.com` | Epic 账号邮箱 (**必须关闭 2FA**) |
 `EPIC_PASSWORD` | `password123` | Epic 账号密码 |
 `GEMINI_API_KEY` | `sk-xxxxxxxx` | [AiHubMix]([推理时代](https://console.aihubmix.com/)) 或 Google 的 API Key |
 `GEMINI_BASE_URL` | `https://aihubmix.com` | 如果使用官方接口，请填 `https://generativelanguage.googleapis.com` |
 `GEMINI_MODEL` | `gemini-2.0-flash-free` | **推荐且默认使用 `gemini-2.0-flash-free`。** 此模型已内置兼容性优化，兼顾性能与成本 |

### 3. 启动工作流
1. 点击仓库上方的 **Actions** 标签页。
2. 如果看到绿色按钮 **I understand my workflows...**，请点击启用。
3. 选择左侧的 `Epic Free Games` 工作流。
4. 点击右侧的 **Run workflow** 手动触发第一次运行测试。

> ✅ **成功提示**：之后的每周，脚本都会根据 `.github/workflows` 中的定时配置自动运行。

---

## 🛠️ 常见问题 (FAQ)

<details>
<summary><b>Q: 为什么日志显示 "Login with Email ... Timeout"?</b></summary>

**A:** 这是因为 GitHub Actions 的共享 IP 段可能被 Epic 临时风控。

* **现象**：脚本能打开页面，但在点击登录按钮时无反应。
* **解决**：通常 GitHub 会自动重试。如果连续失败，请等待 1-2 小时后手动重新运行工作流，GitHub 分配新 IP 后即可恢复。

</details>

<details>
<summary><b>Q: 使用中转 API 报错 "400 Bad Request" 或 "File API not supported"?</b></summary>

**A:** 请确保你使用的是本仓库的最新代码。

* 本项目内置了 `utils.py` 补丁，会拦截 Google SDK 的文件上传行为，将其转换为 **Inline Base64** 数据。
* 这完美绕过了中转站对文件上传 API 的限制。

</details>

<details>
<summary><b>Q: 必须关闭二步验证 (2FA) 吗？</b></summary>

**A:** **是的，必须关闭。**
由于脚本运行在无头模式 (Headless) 下，无法处理短信或邮件验证码。请在 Epic 官网账户设置中暂时禁用 2FA。

</details>

---

## ⚠️ 免责声明

* 本项目仅供 Python 学习与技术交流使用。
* 使用脚本自动化操作可能违反 Epic Games 的服务条款，使用者需自行承担风险。
* 请勿将本项目用于任何商业用途。

---

<div align="center">
<b>Enjoy your free games! 🎮</b>
</div>

