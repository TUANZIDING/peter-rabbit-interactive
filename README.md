<p align="center"><img src="play/peter-rabbit/img/ch01-spreadv1.0.webp" width="100%" alt="彼得兔在菜园里的伴读插图"></p>

<h1 align="center">彼得兔互动伴读 · Peter Rabbit Interactive</h1>
<p align="center"><strong>听一句，读一格，把故事带回纸上。</strong><br>A little story. A little adventure.</p>
<p align="center">适合家长陪同的儿童英语练习，每章约 15 分钟。</p>
<p align="center"><a href="README.md">简体中文</a> · <a href="docs/英文说明v1.2.md">English</a></p>
<p align="center"><code>纯静态</code> · <code>英式角色音频</code> · <code>五关练习</code> · <code>本机进度</code></p>
<p align="center"><a href="#quick-start">开始使用</a> ｜ <a href="#workflow">五关路线</a> ｜ <a href="#status">能力状态</a> ｜ <a href="#docs">文档与共创</a></p>
<p align="center"><sub>主图来自用户提供的 AI 插图素材包，展示故事场景。</sub></p>

<a id="quick-start"></a>
## 先用起来

**[打开四章互动伴读](https://tuanziding.github.io/peter-rabbit-interactive/)** · [第一章](https://tuanziding.github.io/peter-rabbit-interactive/play/peter-rabbit/chapter.html?n=1) · [第二章](https://tuanziding.github.io/peter-rabbit-interactive/play/peter-rabbit/chapter.html?n=2) · [第三章](https://tuanziding.github.io/peter-rabbit-interactive/play/peter-rabbit/chapter.html?n=3) · [第四章](https://tuanziding.github.io/peter-rabbit-interactive/play/peter-rabbit/chapter.html?n=4)

家长陪着听一句、说一句，每章五关，完成后回到纸质作业。无需安装或注册。第一次点击“开始”解锁音频，并打开设备音量。

| 有声漫画 · 实际截图 | Find it · 实际截图 |
|---|---|
| ![点气泡听角色台词](docs/有声漫画截图v1.0.jpg) | ![在场景中找物](docs/找一找截图v1.0.jpg) |

也可下载仓库后本地使用。安装 Python 3，进入仓库根目录：

```sh
python3 -m http.server 8817 --bind 0.0.0.0
```

在 Mac 浏览器打开 [本地书架](http://localhost:8817/play/peter-rabbit/)。在同一 Wi-Fi 下，用 iPad Safari 打开 `http://Mac的局域网IP:8817/play/peter-rabbit/`。第一次点击“开始”解锁音频，并打开设备音量。

该站点支持 GitHub Pages 静态托管。从仓库根目录托管时，网页入口是 `/play/peter-rabbit/`；从 Actions 发布时，也可将这个子目录作为完整站点目录。根目录已提供 .nojekyll，全部资源使用相对路径。本仓库通过 main 分支根目录提供 GitHub Pages；根目录入口自动进入书架。

<a id="workflow"></a>
## 五关小冒险

**有声漫画 → 找一找 → 单词卡 → 小剧场 → 填气泡 → 纸质作业**

| 练习 | 怎么玩 |
|---|---|
| 有声漫画 | 点气泡播放，整句高亮；黄底新词可点读，手机左右滑动 |
| Find it | 听提示，在菜园里找六种物品；可放大，热区有触摸容差 |
| 单词卡 | 翻卡、点读，再完成五题听音选图 |
| 小剧场 | 课文中英对照，选择本章角色，轮到孩子的句子静音 |
| 填气泡 | 拖动，或点词再点空格；复数词形有中文提示 |

每关只收一枚印章。进度仅存在本机 localStorage；家长入口可重置。累计前台使用 15 分钟提醒休息。不录音、不使用麦克风、无统计追踪、无外部 CDN。

<a id="status"></a>
## 当前做到哪一步

| 状态 | 内容与边界 |
|---|---|
| 已实现 | 第 1–4 章各五关，共 49 张图片、204 条 Kokoro 英式音频 |
| 已通过资源检查 | 图片和音频引用存在；WebP ≤250 KB、宽 ≤1200px；MP3 64 kbps 单声道 |
| 浏览器验证 | 四章共32组 Chromium/WebKit 完整流程通过；自动化 WebKit 不等同于真实 iPad Safari |
| 用户反馈 | 第一章已报告试用满意，用户已授权第 2–4 章；新增三章可继续实际试用 |
| 首版取舍 | 使用整句高亮；未实现逐词时间对齐或发音评分 |

<details><summary><strong>素材提取、音频生成与检查</strong></summary>

工具只静态解析原脚本顶部的 C 字典和 S/V 声线表，不运行原脚本。模型及虚拟环境放在仓库之外。

```sh
python3 -m venv ~/peter-prep/venv
~/peter-prep/venv/bin/python -m pip install kokoro-onnx soundfile numpy pillow
for chapter in 2 3 4; do
  ~/peter-prep/venv/bin/python tools/extract-chapterv1.1.py --chapter "$chapter" --kit /实际路径/peter-rabbit-interactive-kit.zip
  ~/peter-prep/venv/bin/python tools/make-line-audiov1.1.py --chapter "$chapter" --models ~/peter-prep/models
done
~/peter-prep/venv/bin/python tools/checkv1.1.py
```

第一章提取工具保留为 extract-chapterv1.0.py；已有音频可直接使用，无需安装生成环境。

需要 FFmpeg；模型使用官方 `kokoro-v1.0.onnx` 与 `voices-v1.0.bin`。Kokoro 不可用时可指定 `--fallback`，用 macOS Daniel/Flo。当前交付使用 Kokoro。

浏览器测试安装 Playwright 及 Chromium/WebKit 后，执行 `PETER_QA_CHAPTER=2 node tools/browser-checkv1.1.mjs`；可通过 `PETER_PLAYWRIGHT_MODULE`、`PETER_QA_URL` 和 `PETER_QA_OUTPUT` 指定环境。将 PETER_QA_CHAPTER 依次设为 1、2、3、4 可检查四章。测试会创建独立浏览器上下文，不修改用户浏览器进度。

</details>

<a id="docs"></a>
## 文档与共创

| 内容 | 入口 |
|---|---|
| 完整英文首页 | [English](docs/英文说明v1.2.md) |
| 验证与实际试用 | [验证记录](docs/验证记录v1.2.md) |
| 四章声线与适配 | [来源与声线](docs/素材来源v1.2.md) |
| 来源与许可范围 | [素材来源](docs/素材来源v1.2.md) |

欢迎反馈触点、角色声音和纸质练习衔接。请勿在截图或公开内容中加入孩子姓名、照片或学校。

<p align="center"><strong>Peter Rabbit Interactive</strong><br><a href="https://github.com/TUANZIDING">TUANZIDING</a> · Beatrix Potter · Project Gutenberg #14838</p>

原著在 Project Gutenberg 标示为美国公版，其他地区请核实。插图为用户提供的 AI 生成素材。Fredoka 字体采用 SIL OFL，许可证随字体附带。其他素材的公开授权范围见来源文档。
