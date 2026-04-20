# 医药投研智能体 - 前端项目

基于 Vue 3 + Vite 构建的医药/生物科技行业 AI 驱动股票分析系统前端。

## 🚀 快速开始

### 环境要求

- Node.js 18+
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:5173

### 生产构建

```bash
npm run build
npm run preview
```

## 📁 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口封装
│   │   ├── request.js    # Axios 实例配置
│   │   ├── chat.js       # 对话 & PDF 上传
│   │   ├── stock.js      # 股票数据接口
│   │   └── analysis.js   # 分析接口
│   ├── components/       # 通用组件
│   │   ├── ChatBox.vue   # 对话输入框（支持拖拽 & PDF 上传）
│   │   ├── MessageItem.vue # 消息气泡
│   │   ├── StockGrid.vue # 股票/行业网格（支持自选股）
│   │   ├── StockDetailPanel.vue # 股票详情面板
│   │   ├── StockChart.vue # K线图
│   │   └── MacroPanel.vue # 宏观指标面板
│   ├── views/            # 页面组件
│   │   ├── MainPage.vue  # 主页（拖拽式对话界面）
│   │   ├── DiagnosePage.vue # 企业诊断
│   │   ├── RiskPage.vue  # 风险评估
│   │   └── ReportPage.vue # 报告生成
│   ├── store/            # Pinia 状态管理
│   │   └── chatStore.js  # 对话历史
│   ├── router/           # Vue Router
│   │   └── index.js
│   ├── utils/            # 工具函数
│   │   └── format.js
│   ├── mock/             # Mock 数据
│   │   └── data.js
│   ├── styles.css        # 全局样式
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html
├── package.json
├── vite.config.js
└── .env.example          # 环境变量模板
```

## 🎨 核心功能

### 1. AI 智能对话
- 多轮对话支持
- 拖拽式多标的联合分析
- 实时行情展示
- 对话历史管理

### 2. 股票数据展示
- 实时行情查询
- K线图表（ECharts）
- 财务指标展示
- 研报列表

### 3. 公司诊断
- 雷达图可视化
- 多维度评分（财务健康度、运营效率、风险因子）
- 优劣势分析
- 改进建议

### 4. 风险评估
- 风险信号监测（红/黄/绿）
- 机会识别
- 横向对比分析

### 5. 定制化报告
- 面向不同受众（投资者/管理层/监管机构）
- 趋势图表
- 一键复制

### 6. 自选股管理
- 添加/删除自选股
- 星标标记
- 持久化存储

### 7. PDF 上传
- 上传年报/研报到知识库
- 实时进度显示
- 支持拖拽上传

## 🎯 技术特性

### 前端技术栈
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **图表**: ECharts 5
- **HTTP**: Axios
- **样式**: 原生 CSS + CSS 变量

### 设计特点
- 浅色小清新主题
- 响应式布局（支持移动端）
- 流畅的动画效果
- 拖拽式交互
- 无障碍访问支持

### 性能优化
- 组件懒加载
- 数据缓存机制
- 请求去重
- 防抖/节流

## 🔧 配置

### 环境变量

创建 `.env` 文件：

```bash
# 后端 API 地址
VITE_API_BASE_URL=http://127.0.0.1:8000

# Demo 用户 ID（可选）
VITE_DEMO_USER_ID=1
```

### API 接口

所有接口通过 `src/api/request.js` 统一管理：

- 基础 URL: `VITE_API_BASE_URL`
- 超时时间: 30 秒
- 自动错误处理
- 响应数据自动解包

## 📱 响应式设计

### 断点
- **Desktop**: > 768px
- **Tablet**: 768px - 480px
- **Mobile**: < 480px

### 移动端优化
- 垂直布局
- 隐藏拖拽把手
- 单列网格
- 优化字体大小
- 全宽表单控件

## 🎨 主题配色

```css
--bg-deep:    #f5f8fc;  /* 深背景 */
--bg-panel:   #ffffff;  /* 面板背景 */
--bg-card:    #f8fafc;  /* 卡片背景 */
--border:     #e2e8f0;  /* 边框 */
--accent:     #38bdf8;  /* 主色调（天蓝） */
--accent2:    #a78bfa;  /* 辅助色（紫色） */
--red:        #ef4444;  /* 上涨/危险 */
--green:      #22c55e;  /* 下跌/成功 */
--gold:       #f59e0b;  /* 警告/自选 */
```

## 🔌 API 接口说明

### 对话接口
```javascript
POST /api/chat
{
  "message": "分析恒瑞医药",
  "targets": [{ "symbol": "600276", "name": "恒瑞医药", "type": "stock" }],
  "history": [...]
}
```

### PDF 上传
```javascript
POST /api/upload_pdf
Content-Type: multipart/form-data
file: <PDF文件>
```

### 股票数据
```javascript
GET /api/stock/quote?symbol=600276
GET /api/stock/kline?symbol=600276&days=60
GET /api/stock/companies
```

### 自选股管理
```javascript
GET /api/stock/watchlist?user_id=1
POST /api/stock/watchlist { symbol, user_id }
DELETE /api/stock/watchlist?symbol=600276&user_id=1
```

### 分析接口
```javascript
GET /api/analysis/diagnose?symbol=600276&year=2024
GET /api/analysis/risks?symbols=600276,603259,300015
GET /api/analysis/compare?metric=毛利率&year=2024
GET /api/analysis/trend?symbol=600276&metric=营业总收入
```

## 🐛 常见问题

### 1. 无法连接到后端

**问题**: 前端显示"无法连接到服务器"

**解决方案**:
- 确认后端服务已启动（默认端口 8000）
- 检查 `.env` 文件中的 `VITE_API_BASE_URL` 配置
- 检查防火墙设置

### 2. CORS 错误

**问题**: 浏览器控制台显示跨域错误

**解决方案**:
- 后端需要配置 CORS 允许前端域名
- 开发环境可使用 Vite 代理（见 `vite.config.js`）

### 3. 图表不显示

**问题**: ECharts 图表区域空白

**解决方案**:
- 检查容器是否有明确的高度
- 确认数据格式正确
- 查看浏览器控制台错误信息

### 4. 拖拽功能失效

**问题**: 无法拖拽股票卡片

**解决方案**:
- 确认元素设置了 `draggable="true"`
- 检查 `dragstart` 事件是否正确绑定
- 移动端不支持原生拖拽，需要使用触摸事件

## 📚 开发指南

### 添加新页面

1. 在 `src/views/` 创建组件
2. 在 `src/router/index.js` 添加路由
3. 在 `src/App.vue` 导航菜单添加链接

### 添加新 API

1. 在 `src/api/` 对应文件添加函数
2. 使用 `request` 实例发起请求
3. 返回 Promise

### 样式规范

- 使用 CSS 变量定义颜色
- 组件样式使用 `scoped`
- 全局样式写在 `styles.css`
- 遵循 BEM 命名规范

### 组件规范

- 使用 Composition API
- Props 定义类型和默认值
- Emit 事件使用 `defineEmits`
- 复杂逻辑抽取到 composables

## 🚀 部署

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/frontend/dist;
    index index.html;

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker 部署

```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

- 项目文档: `/c/Users/lenovo/Desktop/说明文档.md`
- 后端代码: `/c/Users/lenovo/Desktop/4c/backend/`

---

**版本**: v0.2.0-alpha  
**最后更新**: 2026-04-20
