# 米家桌面端五页效果图实施计划

状态：五页代码实现与离屏验收完成（2026-09-23）；真实米家账户联调待用户环境验证

基线：`main` / `55dd635`
参考：用户提供的家庭、房间、设备、场景、消息五张效果图。

## 目标与数据原则

在现有 PySide6 应用中还原五张图的共同布局、层级、卡片密度和主要交互。设备、场景、消息、耗材、天气只显示实际接口或本地缓存得到的值。未接入的自动化规则、历史环境趋势、设备未公开的能力显示明确空状态；不在运行界面填入效果图中的示例数字、时间、设备或规则。

## 共用壳层

1. 左侧固定导航：品牌、家庭/房间/设备/场景/消息/设置、底部插画与标语；当前页青绿色选中态，消息角标取消息数。
2. 内容顶栏：页标题/副标题、家庭或城市选择、天气/AQI、消息入口和窗口控制；天气关闭或失败时自然收起。
3. 中间内容区与右侧详情区保持统一的 16–20px 圆角、暖白底、轻阴影与紧凑间距；窄窗口退化为滚动布局，右侧详情可收起。
4. 深色主题沿用语义色，不允许写死浅色背景导致文字不可读。

## 五页实施顺序

| 阶段 | 页面 | 视觉与交互 | 真实数据来源 / 缺失处理 |
| --- | --- | --- | --- |
| 1 | 共用壳层 | 左栏与顶栏、路由、统一详情栏容器 | `settings_store`、`weather_service`、消息数；缺失即隐藏 |
| 2 | 家庭 | 大横幅、四枚状态卡、关注、房间封面、常用设备、右侧概览/灯/窗帘/环境 | 设备、开关、温湿度、耗材；无读数显示“暂无读数” |
| 3 | 房间 | 顶部房间切换、宽幅房间封面、分类设备控制、右侧状态/快捷操作 | 按 `home_name` 和 `room_name` 聚合；趋势无历史数据则空态 |
| 4 | 设备 | 搜索、类别筛选、按房间分组、紧凑设备卡、右侧选中设备控制 | `DeviceInfo` + spec 的 `DeviceDetail` / `PropInfo`；无能力显示详情入口或不可控状态 |
| 5 | 场景 | 手动场景图卡、一键执行、选中场景详情、自动化分区 | `list_scenes` / `run_scene`；无场景为空态，自动化显示未接入说明 |
| 6 | 消息 | 分类、关注统计、消息列表、右侧详情与关联设备操作 | `list_messages` + 耗材/离线状态；不提供虚构原因、处理时间或“忽略”云端操作 |

## 需要先修的基线问题

- `home_page.py` 关注行重复加入了文字和“查看”按钮；常用设备卡存在 `return` 后的遗留代码。
- 侧栏消息角标会被离线设备数覆盖，需由消息数据单独维护。
- 当前设备页仍是旧网格，房间页和消息页只有列表，场景页缺少图卡和详情栏。
- `theme_test` 原先只隐藏到托盘，没有真正关闭窗口；测试退出前强制正常关闭，返回码现为 0。

## 验收

1. 五页都能在 1440×900 逻辑窗口稳定渲染，和五张参考图逐页比对；功能存在时可点，缺失能力有空态。
2. 家庭/房间/设备之间的房间选择、设备选择与右栏数据一致；控制操作继续经 `JobExecutor` 串行调用 `MijiaService`。
3. 无登录、无设备、离线设备、无场景、无消息、天气失败和深浅主题均可显示。
4. `smoke_test`、主题回归和独立离屏页面预览通过；构建资源清单覆盖新增本地图片。

## 实施与验收记录

- 共用壳层：五项导航、动态标题栏、真实消息角标与家庭选择；首页、房间、设备、场景、消息各有对应布局。
- 首页：宽幅客厅摄影横幅、真实状态、关注项、房间和常用设备；房间侧栏补充真实即时温湿度。
- 房间：照片缩略切换、宽幅封面、按类型设备卡、状态与快捷操作；环境趋势为明确空态。
- 设备：名称/型号搜索、类型筛选、房间分组、选中设备状态与详情入口；未知开关能力不伪装为“已关”。
- 场景：手动场景图卡、一键执行、选中详情；描述、关联设备、执行记录和自动化规则均按接口能力显示空态。
- 消息：真实分类、近 24 小时计数、列表和详情；无关联设备标识时不猜测设备。
- 响应式：窄内容区收起右栏，设备卡点击打开现有详情，消息点击弹出正文；浅/深主题都已截图复核。
- 资源：新增无水印摄影封面 `room-photo-living.png`、`room-photo-bedroom.png`、`room-photo-study.png`，由 ImageGen 生成，仅作装饰背景；`build.ps1` 已纳入打包。
- 验证命令：`python -m compileall -q app tests`、`python -m tests.smoke_test`、`python -m tests.shell_pages_test`、`python -m tests.shell_integration_test`、`python -m tests.theme_test`。

摄影封面生成提示词（交付记录）：

1. Living: “Premium photorealistic editorial interior photograph for a smart-home desktop application, one wide 16:9 horizontal composition. Serene contemporary Chinese urban apartment living room: warm off-white walls, light oak wood, cream sofa, low wooden coffee table, floor-to-ceiling windows with soft linen curtains, subtle greenery. Late afternoon golden sunlight, inviting and understated, physically plausible. Keep lower-left free of clutter for a white text overlay added by software. No people, no logos, no text, no letters, no watermark, no interface elements.”
2. Bedroom: “Photorealistic wide 16:9 interior photograph of a warm minimal contemporary smart apartment bedroom, natural oak and cream linen, soft indirect lighting, comfortable bed, pale neutral palette, editorial architectural photography, calm and lived-in. Leave lower left suitable for white app text overlay. No text, letters, watermark, logos, people or UI.”
3. Study: “Single wide 16:9 premium photorealistic interior photograph of a calm contemporary study / home office in a Chinese city apartment: warm oak desk and cabinetry, cream walls, beautiful task lamp, books, plants, window light in late afternoon, minimal warm understated smart-home aesthetic. Composition suitable for a room card with white text overlay in lower-left. No people, no letters or readable text, no logos, no watermarks, no interface.”
