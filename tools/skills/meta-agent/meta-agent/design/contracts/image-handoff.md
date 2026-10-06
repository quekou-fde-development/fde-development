# 契约 · 出图交接（Codex image_gen）

**权威源**：本件。**消费方**：`fde-meta-agent`、`builder-agent`。**出图执行体**：Codex 内置 `built-in image_gen.imagegen`（夏洛克裁定）。

skill 不出图。skill 做三件：写请求单、过 QA 闸、上传与哈希回读。

## 一 · 链路

```
skill ──image-request.json──▶ Codex 出图 ──PNG 成对──▶ skill 质检 ──QA 过──▶ 上传 ──▶ 哈希回读
                ▲                                            │
                └────────── QA 未过：带原因重出 ◀─────────────┘
```

链路分段的目的：出图是无确定性的一步（同一提示词两次结果不同），把它与上传隔开，失败重出的代价限于该对图。

## 二 · 请求单结构

```json
{
  "schema_version": "image-request-09.20.1",
  "release": "09.20",
  "batch": "20260919-employee-portraits",
  "tool": "built-in image_gen.imagegen",
  "mode": "reference-guided new employee portraits and paired display images",
  "series_style_ref": {"path": "contracts/series-style-09.20.json", "sha256": "0af3bd6eed30ab76a60771a1b24a97b276a7e9f537e824d23878e282a2daac6f"},
  "requests": [
    {
      "key": "chen-wenjin",
      "target": {"name": "陈文锦", "seat": "m3_i", "surface": "fde"},
      "refs": {
        "identity": "references/chen-wenjin.png",
        "style": ["originals/18-avatar.png", "originals/12-avatar.png"]
      },
      "character": {"actor": "陶珞依", "show": "终极笔记", "year": 2020,
                    "face_hair_costume": "..."},
      "prompts": {"avatar": "...", "bio": "..."}
    }
  ]
}
```

`requests[]` 一席一项，每项产出**一对**（avatar + bio）。头像与亮相图必须同批同身份——分两次出会出现同一人两张脸。

## 三 · 系列风格块（整块复用，禁止逐席改写）

正文落 `contracts/series-style-09.20.json`（sha256 `0af3bd6eed30ab76a60771a1b24a97b276a7e9f537e824d23878e282a2daac6f`），取自 09.14 `style-audit.json#series_style`，逐字：

| 项 | 值 |
|---|---|
| `medium` | 影视级写实人像，肤质及织物真实；角色服装服从影视版本 |
| `background` | 中式民国木质书房/档案室；主体后方深海军蓝面 |
| `brand_motif` | 两侧钴蓝缺口方框、细蓝弯曲连线、小量橙色节点；不增加文字 |
| `palette` | 近黑海军蓝、钴蓝、暖胡桃木、米白纸张、极小橙点；角色服装可保留识别色 |
| `lighting` | 暖色侧前方柔光，右侧低强度冷蓝发丝轮廓，暗背景与清晰自然面部 |
| `avatar` | 方形居中胸像，完整头顶，清晰眼神，与同人展示图服装发型一致；旧图512x512 |
| `bioPicture` | 横向工作场景，中近景半身、角色居中或略偏一侧、木桌与岗位相关少量道具；旧图1536x896 |

尺寸：头像 1024×1024，亮相图 1536×896；512×512 为旧规格，只用于比对既有资产。系列参考图索引 [12, 13, 14, 15, 16, 17, 18, 19, 20]。

请求单只引用该文件的路径与哈希，不内联副本。逐席改写风格块会破坏系列一致性。

## 四 · 提示词模板

### 4.1 头像

前缀（固定）：

> Use case: photorealistic-natural … Image 1 defines ONLY the new character identity and costume. Images 2-3 are STRICT style/framing references; do not borrow their faces … cobalt-blue open square bracket frame, a single thin curved blue line with a tiny orange point … Output one 1024x1024 square image

`…` 处填系列风格块对应句。前缀后接逐席块：

```
Character: <name>
Played by: <actor> in <show> (<year>)
Face/hair/costume: <face_hair_costume>
```

「do not borrow their faces」必须原样出现。参考图里的系列演员脸不得渗入新角色。

### 4.2 亮相图

> Use case: identity-preserve … Image 1 is the already approved identity and costume … wide landscape working-scene … ideally 1536x896

`refs.identity` 指向**刚过 QA 的头像**，不是人物参考图。这保证了头像与亮相图之间的身份连续——亮相图必须与头像同脸，与人物参考同脸则不必。

## 五 · QA 闸

```json
{"status": "PASS", "target_count": 11, "asset_count": 22,
 "review_method": "identity and costume continuity between each pair, navy/cobalt/walnut palette, light direction, blue brackets and orange node, crop, hands, absence of visible text or watermark",
 "rows": [{"key": "...", "name": "...", "approved": true,
           "assets": {"avatar": {"path": "...", "width": 1024, "height": 1024, "bytes": 0, "sha256": "..."},
                      "bio":    {"path": "...", "width": 1536, "height": 896,  "bytes": 0, "sha256": "..."}}}]}
```

闸规：

1. **逐张** `approved`，不是逐对。同一对里头像过、亮相图不过，即整对重出。
2. 复核者**不得是出图执行体自己**（Codex 不自证）。
3. `status` 置 `PASS` 的条件是 `target_count` 与 `asset_count` 与请求单核对相等，且全部 `approved=true`。计数不符即 `COUNT_MISMATCH`。
4. 未过闸的图像**不得上传**。上传脚本硬断言 `qa.status=PASS`、计数、以及该 key 的 `approved`，任一不满足即退出。

## 六 · 上传与回读

### 6.1 FDE 面

```
POST /private-digiworkers/{avatar|bio-picture}:upload-url   body {"contentType":"image/png"}
  → {uploadUrl, previewToken}
PUT <uploadUrl>                                              --upload-file <png>
PATCH /private-digiworkers/{id}                              {avatarPreviewToken | bioPicturePreviewToken}
```

- 上传用 `curl --config -`，URL 经 stdin 传入，避免出现在进程参数里。
- 上传前断言：PNG 魔数（`bytes[1..4] === 'PNG'`）、`length < 20 MB`、QA 已过、该席名称与基线一致。
- 回读：从 `pub.autostaff.cn` 下载服务端图像，**像素哈希**（`ensureAlpha().raw()` 后哈希）与本地相等才算过。字节哈希作为附带证据。下载只允许 `pub.autostaff.cn` 主机。

### 6.2 Builder 面

```
octopus-builder-cli workers upload-avatar      <workerId> --file <png>
octopus-builder-cli workers upload-bio-picture <workerId> --file <png>
```

回读 worker 对象，断言 `avatarUrl` / `bioPictureUrl` 非空且主机为 `pub.autostaff.cn`。像素哈希回读同 FDE 面。

## 七 · 失败处置

| 现象 | 处置 |
|---|---|
| QA 未过 | 带 `review_method` 对应原因重出，同一 key 最多三轮；三轮不过升级人工 |
| 身份漂移（头像与亮相图不同脸） | 重出亮相图，`refs.identity` 确认指向已过 QA 的头像 |
| 风格漂移（背景 / 纹样 / 配色偏离） | 检查参考图二、三是否在位；不在位即重建请求单 |
| 计数不符 | 停手，不部分上传 |
| 像素哈希不等 | 重传一次；仍不等即报 `IMAGE_READBACK_MISMATCH` 并保留两份图 |
