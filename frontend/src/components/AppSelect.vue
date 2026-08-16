<template>
  <div class="app-select" ref="rootRef">
    <button
      type="button"
      class="app-select__trigger"
      :class="{ 'is-open': open }"
      :aria-haspopup="'listbox'"
      :aria-expanded="open ? 'true' : 'false'"
      @click="toggle"
    >
      <span class="app-select__value" :class="{ 'is-placeholder': !selectedLabel }">
        {{ selectedLabel || placeholder }}
      </span>
      <svg
        class="app-select__chevron"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <!-- 用 Teleport 渲染到 body，避免被弹窗的 overflow 裁剪 -->
    <Teleport to="body">
      <div v-if="open" class="app-select__backdrop" @mousedown.prevent="close"></div>
      <div
        v-if="open"
        ref="menuRef"
        class="app-select__menu"
        :class="{ 'is-positioned': positioned }"
        :style="menuStyle"
        role="listbox"
      >
        <input
          v-if="searchable"
          ref="searchRef"
          v-model="query"
          type="text"
          class="app-select__search"
          :placeholder="searchPlaceholder"
          @keydown.esc="close"
        />
        <ul class="app-select__options">
          <li
            v-for="opt in filteredOptions"
            :key="String(opt.value)"
            class="app-select__option"
            :class="{ 'is-selected': String(opt.value) === String(modelValue) }"
            role="option"
            :aria-selected="String(opt.value) === String(modelValue)"
            @click="choose(opt)"
          >
            <span class="app-select__label">{{ opt.label }}</span>
            <svg
              v-if="String(opt.value) === String(modelValue)"
              class="app-select__check"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </li>
          <li v-if="!filteredOptions.length" class="app-select__empty">无匹配项</li>
        </ul>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue';

export interface AppSelectOption {
  value: string | number;
  label: string;
}

const props = withDefaults(defineProps<{
  modelValue?: string | number | null;
  options?: AppSelectOption[];
  placeholder?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
}>(), {
  modelValue: null,
  options: () => [],
  placeholder: '请选择',
  searchable: true,
  searchPlaceholder: '搜索...',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void;
}>();

const open = ref(false);
const positioned = ref(false);
const query = ref('');
const rootRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const searchRef = ref<HTMLInputElement | null>(null);
const menuStyle = ref<Record<string, string>>({});

const selectedLabel = computed(() => {
  const opt = props.options.find(o => String(o.value) === String(props.modelValue));
  return opt ? opt.label : '';
});

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.options;
  return props.options.filter(o => o.label.toLowerCase().includes(q));
});

function toggle() {
  if (open.value) {
    close();
    return;
  }
  open.value = true;
  query.value = '';
  nextTick(() => {
    positionMenu();
    if (props.searchable && searchRef.value) {
      searchRef.value.focus();
    }
  });
}

function choose(opt: AppSelectOption) {
  emit('update:modelValue', opt.value);
  close();
}

function close() {
  open.value = false;
  positioned.value = false;
}

function positionMenu() {
  const trigger = rootRef.value;
  const menu = menuRef.value;
  if (!trigger || !menu) return;
  const rect = trigger.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const margin = 8;
  const spaceBelow = vh - rect.bottom;
  const menuHeight = menu.offsetHeight;
  // 下方空间不足时向上展开
  const openUp = menuHeight > spaceBelow - margin && rect.top > spaceBelow;
  const left = Math.max(margin, Math.min(rect.left, vw - margin));
  const width = Math.min(Math.max(rect.width, 220), vw - margin * 2);
  if (openUp) {
    menuStyle.value = {
      position: 'fixed',
      left: `${left}px`,
      bottom: `${vh - rect.top + margin}px`,
      width: `${width}px`,
      maxHeight: `${Math.max(rect.top - margin, 160)}px`,
    };
  } else {
    menuStyle.value = {
      position: 'fixed',
      left: `${left}px`,
      top: `${rect.bottom + margin}px`,
      width: `${width}px`,
      maxHeight: `${Math.max(spaceBelow - margin, 160)}px`,
    };
  }
  positioned.value = true;
}

let rafId = 0;
function onScrollOrResize() {
  if (!open.value) return;
  cancelAnimationFrame(rafId);
  rafId = requestAnimationFrame(positionMenu);
}

onMounted(() => {
  // scroll 不冒泡，用 capture 捕获弹窗等容器内部的滚动，保持下拉菜单跟随触发按钮
  document.addEventListener('scroll', onScrollOrResize, { capture: true, passive: true });
  window.addEventListener('resize', onScrollOrResize);
});

onBeforeUnmount(() => {
  document.removeEventListener('scroll', onScrollOrResize, { capture: true } as EventListenerOptions);
  window.removeEventListener('resize', onScrollOrResize);
  cancelAnimationFrame(rafId);
});
</script>

<style scoped>
.app-select {
  position: relative;
}

.app-select__trigger {
  width: 100%;
  min-height: 44px;
  padding: 12px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  color: #333;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  text-align: left;
}

.app-select__trigger.is-open {
  border-color: #4a90d9;
}

.app-select__value.is-placeholder {
  color: #999;
}

.app-select__chevron {
  flex-shrink: 0;
  color: #888;
  transition: transform 0.2s;
}

.app-select__trigger.is-open .app-select__chevron {
  transform: rotate(180deg);
}

/* Teleport 到 body，scoped 属性仍会保留，以下样式可正常作用 */
.app-select__backdrop {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: transparent;
}

.app-select__menu {
  position: fixed;
  z-index: 1101;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  max-height: 60vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-select__menu:not(.is-positioned) {
  opacity: 0;
}

.app-select__search {
  flex-shrink: 0;
  margin: 8px 8px 4px;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  min-height: 40px;
}

.app-select__options {
  list-style: none;
  margin: 0;
  padding: 4px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.app-select__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px;
  border-radius: 6px;
  font-size: 16px;
  color: #333;
  cursor: pointer;
}

.app-select__option:active {
  background: rgba(74, 144, 217, 0.12);
}

.app-select__option.is-selected {
  color: #4a90d9;
  font-weight: 500;
}

.app-select__empty {
  padding: 16px;
  text-align: center;
  color: #999;
  font-size: 14px;
}
</style>
