<template>
  <Teleport to="body">
    <div v-if="modelValue" class="geo-overlay" role="dialog" aria-modal="true" aria-labelledby="geo-title">
      <div class="geo-panel">
        <div class="geo-panel__hero">
          <div class="geo-panel__iconWrap" aria-hidden="true">
            <svg class="geo-panel__pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 21s7-4.5 7-11a7 7 0 1 0 -14 0c0 6.5 7 11 7 11z" />
              <circle cx="12" cy="10" r="2" fill="currentColor" stroke="none" />
            </svg>
          </div>
          <h2 id="geo-title" class="geo-panel__title">开启定位权限</h2>
          <p class="geo-panel__lead">距离排序需要获取您的大致位置。若曾拒绝授权，可按下方说明在系统或浏览器中重新打开。</p>
        </div>

        <div class="geo-panel__body">
          <section class="geo-step">
            <span class="geo-step__badge">iOS · Safari</span>
            <p class="geo-step__text">
              打开<strong>设置</strong> → <strong>Safari 浏览器</strong> → <strong>位置</strong>，选择「询问」或「允许」；或进入
              <strong>设置</strong> → <strong>隐私与安全性</strong> → <strong>定位服务</strong>，找到本应用/浏览器并允许。
            </p>
          </section>
          <section class="geo-step">
            <span class="geo-step__badge">Android · Chrome</span>
            <p class="geo-step__text">
              点击地址栏左侧<strong>锁形或信息图标</strong> → <strong>网站设置 / 权限</strong> → 将<strong>位置</strong>设为「允许」；或在系统
              <strong>设置 → 应用 → Chrome → 权限</strong> 中开启位置。
            </p>
          </section>
          <section class="geo-step">
            <span class="geo-step__badge">微信内置浏览器</span>
            <p class="geo-step__text">
              部分环境下需在微信中：<strong>我 → 设置 → 个人信息与权限 → 系统权限管理</strong>，或为页面单独允许位置权限。
            </p>
          </section>
          <section class="geo-note">
            <span class="geo-note__dot" aria-hidden="true" />
            <p>
              请尽量使用 <strong>HTTPS</strong> 访问本页；若仍无法定位，可在管理后台配置<strong>百度地图 AK</strong>作为备用方案。
            </p>
          </section>
        </div>

        <div class="geo-panel__actions">
          <button type="button" class="geo-btn geo-btn--ghost" @click="emitRetry">重新尝试定位</button>
          <button type="button" class="geo-btn geo-btn--primary" @click="emitClose">我知道了</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "retry"): void;
}>();

function emitClose() {
  emit("update:modelValue", false);
}

function emitRetry() {
  emit("retry");
}
</script>

<style scoped>
.geo-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: env(safe-area-inset-top, 0) 12px calc(12px + env(safe-area-inset-bottom, 0));
}

.geo-panel {
  width: 100%;
  max-width: 28rem;
  max-height: min(85vh, 720px);
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 20px 20px 14px 14px;
  box-shadow:
    0 -4px 32px rgba(14, 116, 144, 0.12),
    0 0 0 1px rgba(255, 255, 255, 0.8) inset;
  overflow: hidden;
}

.geo-panel__hero {
  padding: 20px 18px 14px;
  background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 42%, #0284c7 100%);
  color: #f0f9ff;
  flex-shrink: 0;
}

.geo-panel__iconWrap {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.geo-panel__pin {
  width: 26px;
  height: 26px;
  color: #fff;
}

.geo-panel__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}

.geo-panel__lead {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.55;
  opacity: 0.95;
}

.geo-panel__body {
  flex: 1;
  overflow: auto;
  padding: 14px 16px 8px;
  -webkit-overflow-scrolling: touch;
}

.geo-step {
  margin-bottom: 12px;
  padding: 12px 12px 12px 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.geo-step__badge {
  display: inline-block;
  margin-bottom: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #0369a1;
  background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%);
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.geo-step__text {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: #334155;
}

.geo-step__text strong {
  color: #0f172a;
  font-weight: 700;
}

.geo-note {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-top: 4px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(254, 243, 199, 0.65);
  border: 1px solid rgba(251, 191, 36, 0.35);
}

.geo-note__dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.25);
}

.geo-note p {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.55;
  color: #78350f;
}

.geo-note strong {
  font-weight: 700;
}

.geo-panel__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px calc(14px + env(safe-area-inset-bottom, 0));
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  flex-shrink: 0;
  background: rgba(248, 250, 252, 0.96);
}

.geo-btn {
  width: 100%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-weight: 700;
  cursor: pointer;
  border: none;
  touch-action: manipulation;
}

.geo-btn--primary {
  color: #fff;
  background: linear-gradient(120deg, #0284c7 0%, #0369a1 55%, #0e7490 100%);
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
}

.geo-btn--ghost {
  color: #0369a1;
  background: #fff;
  border: 1px solid rgba(56, 189, 248, 0.55);
}

@media (min-width: 1024px) {
  .geo-overlay {
    align-items: center;
    justify-content: center;
    padding: 24px;
  }

  .geo-panel {
    max-width: min(32rem, 100%);
    border-radius: 18px;
    box-shadow:
      0 24px 56px rgba(15, 23, 42, 0.12),
      0 0 0 1px rgba(148, 163, 184, 0.1);
  }
}
</style>
