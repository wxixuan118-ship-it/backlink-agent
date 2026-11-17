# 外链方案 2026-11-17

数据来源：4 份 Ahrefs Backlinks 导出（`current-page-20261117-211452 / 212227 / 212306 / 212337`），覆盖 3 个站：

| 站点 | 导出文件 | 链接数 | 真实外链 | 垃圾外链 | 判断 |
|---|---|---|---|---|---|
| aquariumstocking.com | 212337 | 100 | 9 | 91 | 编辑外链已跑通，品种页对口互换，可持续放量 |
| aquariumstockingcalculator.com | 211452 | 97 | 4 | 93 | 刚起步，仅 2 个真实站，需要补量 |
| getaquariumtracker.app | 212227 + 212306 | 193 | 5 | 188 | 风险最高：真实链极少却背了近 200 条 PBN，比例严重失衡 |

合计：**18 条真实外链**，**188 个垃圾域名**（清单见 `disavow-2026-11-17.txt`）。

---

## 一、可参考的真实外链（按价值排序）

### A. 品种页 ↔ 品种页 对口互换（最值得复制）

| 来源页 | 指向 | 锚文本 |
|---|---|---|
| aquaverdia.world/planted-aquariums/blue-phantom-pleco-planted-tank/ | aquariumstocking.com/fish/blue-phantom-pleco | aquariumstocking.com's Blue Phantom guide |
| freshwaterguides.com/fish/beginner-freshwater-fish/ | aquariumstocking.com/fish/tiger-barb | AquariumStocking's care and aggression notes |
| flowerhornhobby.com/care/ | aquariumstocking.com/fish/flowerhorn-cichlid | Flowerhorn Cichlid Care Guide |
| scapeeden.com/wiki/inverts/tylomelania-spp | aquariumstocking.com/fish/rabbit-snail | AquariumStocking: rabbit snail |
| goodfishkeeping.com/species/blue-acara | aquariumstockingcalculator.com/species/blue-acara | aquariumstockingcalculator.com |
| goodfishkeeping.com/species/cobalt-zebra | aquariumstocking.com/fish/cobalt-blue-zebra | aquariumstocking.com |
| aquaristatlas.com/bichirs/polypterus-congicus/ | aquariumstockingcalculator.com/species/congo-bichir | Aquarium Stocking Calculator — Congo bichir care guide |

要点：
- 全部落在**具体品种页**，不是首页。
- 锚文本统一是「品牌 + 品种/指南」复合形式，既带品牌词又带品种词，非纯关键词堆砌。
- goodfishkeeping.com **在两个站各挂一条品种页链**，是可反复合作的长期伙伴，优先维护。

### B. 工具页引用（工具类站最有效的打法）

| 来源页 | 指向 | 锚文本 | 备注 |
|---|---|---|---|
| re-thinkingthefuture.com/architectural-insights/the-unexpected-return-of-built-in-aquariums-... | aquariumstocking.com/calculator | aquarium stocking calculator | AS 11，建筑类站，2026-02 上线且仍在 |
| aquariumsource.com/aquarium-fish-stocking-guide/ | aquariumstocking.com/calculator | fish stocking calculator | AS 6，主题高度对口 |
| aquariumtales.com/how-many-gallons-is-my-fish-tank/ | getaquariumtracker.app/tools/aquarium-volume-calculator | Aquarium Tracker, Aquarium Volume Calculator | 2 天前新增，站点活跃 |
| petfel.com/co2-level-calculator/ | aquariumstocking.com/aquarium-co2-calculator | aquariumstocking.com | 4 天前新增 |
| aquariumcraftlog.com/general/what-is-the-best-fresh-water-pet-fish | aquariumstockingcalculator.com/ | Aquarium Stocking Calculator | 品牌词打首页 |

### C. 目录收录 / 官方页（低权重，但可批量）

| 来源 | 指向 | 说明 |
|---|---|---|
| askmatchbox.com/solutions/aquarium-tracker-tank-manager | getaquariumtracker.app/ | AI 工具目录，锚文本 “Website”，可批量复制到同类目录 |
| apps.apple.com/us/app/aquarium-tracker-tank-manager/id6755304265 | getaquariumtracker.app/ | 官方 Developer Website，**nofollow**，不算外链成果 |
| www.ukaps.org 论坛帖 /79049/ | getaquariumtracker.app/get-app | AS 7，但状态已是 **Lost: Bot blocked**；只适合真实用户身份参与讨论 |
| aibusinesssites.com/blog/how-to-choose-the-right-ai-assistant-... | getaquariumtracker.app/features/aquarium-ai | AI 生成内容站，链接形式生硬，不作标杆 |
| reddlx.com/author/BaronMason | aquariumstocking.com/calculator | Reddit 抓取镜像页，价值低 |
| storetally.com/ext/googleplay/com.aquariummanager.fishi | aquariumstockingcalculator.com/ | 应用商店数据聚合页，多为 nofollow |

---

## 二、垃圾外链特征（用于后续识别，不再参考）

- **PBN 模板站群（占绝大多数）**：路径为 `/citation-network/`、`/pbn-directory/`、`/link-placement-hub/`、`/all/1180/11.html`、`/all/60/34.html`，外链数 3000–5000、内链仅 2；锚文本统一为 “High Quality Dofollow Backlinks DA 50 PA 40 Premium PBN Network Service …”。
- **统计/报告/share 垃圾站**：`/stats/13642`、`/report/13641`、`/share/13641` + 标题 “✅ Website Stats 📊”“👲 Domain Report”，外链 3500，**全部 nofollow**。
- **backlink 卖家评测页**：backlinknest.xyz / backlinkforge.xyz / backlinkdock.xyz / backlinkbase.xyz / authoritydock.xyz，同一句 “Traffic Increased by 300%! Thanks to grow-your.store PBN Links”，外链 10001。
- **图片链目录**：8coint.com/list.php，图片锚文本，无效。

风险关联：三个站有 **22 个垃圾域名完全重叠**（dapio.shop、cmocheatsheets.com、bestwebs12341.site、casinooftheking.com …），说明是同一个 PBN 供应商在做站群，风险会顺着域名关联传导。三个站的 disavow 必须一起做。

---

## 三、执行方案

### 第 1 步：止损（本周）

1. 三个站在 Search Console 分别提交 disavow 文件：`disavow-2026-11-17.txt`（188 个域名，一次文件可三站通用）。
2. 提交前先看 GSC「安全问题和手动操作」是否有处罚记录；有处罚则同时提交重新审核请求。
3. 停止一切 PBN / 站群 / 目录群发购买，新增外链只走编辑链接或真实目录。

### 第 2 步：复制已验证的打法（本月）

优先级按 ROI：

1. **品种页互换**（最高 ROI）：以 aquariumstocking.com 的 7 条为模板，向 aquaverdia / freshwaterguides / flowerhornhobby / scapeeden / goodfishkeeping 追加新品种页；文案用「我方品种页 ↔ 对方品种页」一一对应，锚文本用「品牌 + 品种」。
2. **工具页引用**：aquariumsource、re-thinkingthefuture、aquariumtales、petfel 这类已有工具页引用的站，继续补 /calculator、/aquarium-co2-calculator、/tools/* 的被引用机会。
3. **AI/工具目录**：askmatchbox 已验证可收录，按 backlink-agent 的目录清单批量提交（自动化已覆盖）。

### 第 3 步：外链结构规范

- 深页优先：真实外链全部落在品种页/工具页，而垃圾链 90/93 打首页 —— 首页链占比过高本身就是风险信号。
- 锚文本：品牌 + 具体品种 / 品牌 + 具体工具，禁止 “buy backlinks”“cheap SEO” 类词。
- 每站每月真实编辑链接 ≥ 5 条；连续两个月真实链 < 5 条时，暂停任何目录批量提交，先补编辑链。

---

## 四、本次交付

1. 188 个垃圾域名已整理成 `disavow-2026-11-17.txt`（Google disavow 格式，可直接上传）。
2. `config/sites.yaml` 新增站点 `lightvela`（https://lightvela.com），用于触发自动目录提交。
3. 真实外链目标尚未进入自动化（需要人工邮件外联），本文件第一节即为外联清单。
