# Coding Rules

- Python 遵循 PEP 8、类型标注和格式化/静态检查；TypeScript 开启 strict，禁止 `any` 逃避类型。
- 领域逻辑写成小而可测试的纯函数或服务；路由、ORM 和模型调用仅做适配，不承载复杂决策。
- 所有外部调用设置超时、有限重试和明确异常映射；不要吞异常或向用户暴露堆栈。
- 使用结构化日志并带 `request_id`/`job_id`；不得记录密钥、令牌、完整库存或原始私密对话。
- 配置来自环境变量和受版本控制的示例配置；严禁硬编码模型地址、凭据、阈值和路径。
- 提交前运行格式化、静态检查与相关测试；修复根因，避免复制粘贴和无说明的 `TODO`。
- 变更数据库需迁移、回滚说明和测试；变更 API/Prompt/评分须更新对应文档与版本号。

单元测试覆盖规则、解析、权限和错误分支；集成测试覆盖 API、数据库、任务与向量库适配；端到端测试覆盖库存到推荐、草稿到发布两个主流程。缺陷修复先补回归测试（无法测试时在 PR/变更说明中解释）。

## 前端响应式编码规范

### CSS 规范

1. **使用移动优先（Mobile First）写法**：
   ```css
   /* 基础样式为移动端 */
   .component {
     padding: 16px;
   }
   
   /* 平板端及以上 */
   @media (min-width: 768px) {
     .component {
       padding: 20px;
     }
   }
   ```

2. **避免固定宽度**：使用百分比、`max-width` 或 CSS Grid/Flexbox

3. **触摸友好**：
   - 按钮最小高度：44px
   - 输入框最小高度：44px
   - 输入框字体大小：16px（防止 iOS 缩放）

### JavaScript/TypeScript 规范

1. **使用 `useResponsive` 工具**：
   ```typescript
   import { useResponsive } from '../composables/useResponsive';
   
   const { isMobile, isTablet, isDesktop } = useResponsive();
   ```

2. **条件渲染**：根据设备类型渲染不同组件或布局

3. **事件处理**：移动端避免 hover 效果，使用点击事件

### 测试规范

1. 在 375px、768px、1024px 宽度下测试
2. 验证触摸目标尺寸
3. 检查表单输入不会触发 iOS 缩放

