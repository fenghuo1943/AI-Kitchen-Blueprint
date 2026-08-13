<template>
  <div class="menu">
    <div class="header">
      <div class="mode-switch">
        <button :class="['mode-btn', mode === 'calendar' ? 'active' : '']" @click="mode = 'calendar'">日历</button>
        <button :class="['mode-btn', mode === 'waterfall' ? 'active' : '']" @click="switchWaterfall">瀑布流</button>
      </div>
    </div>

    <!-- 日历模式 -->
    <div v-if="mode === 'calendar'">
      <div class="calendar-nav">
        <button class="btn btn-secondary" @click="shiftMonth(-1)">‹ 上月</button>
        <span class="month-title" @click="openDatePicker">{{ currentMonthLabel }} ▾</span>
        <button class="btn btn-secondary" @click="shiftMonth(1)">下月 ›</button>
      </div>
      <div class="calendar">
        <div class="weekday" v-for="w in ['日','一','二','三','四','五','六']" :key="w">{{ w }}</div>
        <div
          v-for="cell in calendarCells"
          :key="cell.key"
          :class="['day', {
            'blank': !cell.date,
            'has-menu': cell.hasMenu,
            'today': cell.isToday,
            'selected': cell.isSelected
          }]"
          @click="cell.date && selectDay(cell.date)"
        >
          <span class="day-num">{{ cell.dayNum }}</span>
        </div>
      </div>

      <!-- 选中日期的菜单 -->
      <div v-if="dayMenu" class="day-detail">
        <div v-if="dayMenu.ing_list.length || dayMenu.sea_list.length" class="shopping-list">
          <div v-if="dayMenu.ing_list.length" class="shopping-row">
            <h3>🥬 今日食材</h3>
            <div class="shop-chips">
              <span v-for="ing in dayMenu.ing_list" :key="ing.id" class="shop-chip">{{ ing.name }}</span>
            </div>
          </div>
          <div v-if="dayMenu.sea_list.length" class="shopping-row">
            <h3>🧂 今日调料</h3>
            <div class="shop-chips">
              <span v-for="sea in dayMenu.sea_list" :key="sea.id" class="shop-chip sea">{{ sea.name }}</span>
            </div>
          </div>
        </div>

        <div v-if="dayMenu.list.length" class="day-recipes">
          <div v-for="item in dayMenu.list" :key="item.recipe_id" class="day-recipe">
            <div class="day-recipe-info" @click="goDetail(item.recipe_id)">
              <span class="recipe-title">{{ item.title }}</span>
              <span v-if="item.cook_time" class="recipe-time">⏱️ {{ item.cook_time }}分钟</span>
            </div>
            <button class="btn-small btn-danger" @click="removeFromDay(item.recipe_id)">移除</button>
          </div>
        </div>
        <div v-else class="empty-day">当天没有安排菜谱</div>
      </div>

      <!-- 年月快速选择弹窗 -->
      <div v-if="showDatePicker" class="date-picker-mask" @click.self="showDatePicker = false">
        <div class="date-picker">
          <h3 class="date-picker-title">选择年月</h3>
          <div class="picker-wheels">
            <div
              class="wheel"
              @pointerdown.prevent="wheelDown($event, 'year')"
              @wheel.prevent="onWheelScroll($event, 'year')"
            >
              <div class="wheel-mask">
                <div
                  v-for="item in yearItems"
                  :key="item.key"
                  class="wheel-item"
                  :class="{ active: item.active }"
                  :style="itemStyle(item)"
                >{{ item.label }}</div>
                <div class="wheel-center"></div>
              </div>
              <div class="wheel-caption">年</div>
            </div>
            <div
              class="wheel"
              @pointerdown.prevent="wheelDown($event, 'month')"
              @wheel.prevent="onWheelScroll($event, 'month')"
            >
              <div class="wheel-mask">
                <div
                  v-for="item in monthItems"
                  :key="item.key"
                  class="wheel-item"
                  :class="{ active: item.active }"
                  :style="itemStyle(item)"
                >{{ item.label }}</div>
                <div class="wheel-center"></div>
              </div>
              <div class="wheel-caption">月</div>
            </div>
          </div>
          <div class="picker-actions">
            <button class="btn btn-secondary" @click="showDatePicker = false">取消</button>
            <button class="btn btn-primary" @click="confirmDatePicker">确定</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 瀑布流模式 -->
    <div v-else>
      <div v-for="group in waterfall" :key="group.date" class="waterfall-group">
        <h2 class="waterfall-date">{{ group.date }}</h2>
        <div class="waterfall-recipes">
          <div v-for="item in group.recipes" :key="item.recipe_id" class="waterfall-recipe" @click="goDetail(item.recipe_id)">
            <span class="recipe-title">{{ item.title }}</span>
            <span v-if="item.cook_time" class="recipe-time">⏱️ {{ item.cook_time }}分钟</span>
          </div>
        </div>
      </div>
      <div v-if="!waterfall.length" class="empty-state">还没有安排菜单，去菜谱库「加入菜单」吧</div>
      <div v-if="waterfall.length" class="load-more">
        <span v-if="loadingMore" class="loading">加载中...</span>
        <span v-else-if="loadError" class="error">
          加载失败
          <button class="btn btn-secondary btn-small" @click="loadWaterfall(false)">重试</button>
        </span>
        <span v-else-if="!hasMore" class="end">—— 到底了 ——</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { menuApi } from '../services/api';
import { toast } from '../composables/useToast';
import type { MenuByDate } from '../types';

const router = useRouter();
const mode = ref<'calendar' | 'waterfall'>('calendar');

const today = new Date();
const currentYear = ref(today.getFullYear());
const currentMonth = ref(today.getMonth()); // 0-11
const monthDates = ref<string[]>([]);
const dayMenu = ref<MenuByDate | null>(null);
const selectedDate = ref('');

// 年月快速选择弹窗（滚轮式）
const showDatePicker = ref(false);
const ITEM_H = 40; // 滚轮每行高度 px
const yearOffset = ref(currentYear.value); // 年份偏移（连续值，拖拽时可为小数）
const monthOffset = ref(currentMonth.value); // 月份偏移（连续值，可无限循环）

const pickYear = computed(() => Math.round(yearOffset.value));
const pickMonth = computed(() => ((Math.round(monthOffset.value) % 12) + 12) % 12);

// 生成滚轮当前窗口内的可见项（中心 ±2 行），wrap=true 时按 12 取模实现无限循环
function wheelItems(offset: number, formatter: (display: number) => string, wrap = false) {
  const c = Math.round(offset);
  const items: { key: string; label: string; y: number; active: boolean; dist: number }[] = [];
  for (let i = -2; i <= 2; i++) {
    const v = c + i;
    const disp = wrap ? ((v % 12) + 12) % 12 : v;
    items.push({
      key: `${wrap ? 'm' : 'y'}-${v}`,
      label: formatter(disp),
      y: (v - offset) * ITEM_H,
      active: v === c,
      dist: Math.abs(v - offset)
    });
  }
  return items;
}

const yearItems = computed(() => wheelItems(yearOffset.value, (v: number) => `${v}年`));
const monthItems = computed(() => wheelItems(monthOffset.value, (v: number) => `${v + 1}月`, true));

// 根据距中心的距离计算位移与透明度
function itemStyle(item: { y: number; dist: number }) {
  const opacity = Math.max(0.2, 1 - item.dist * 0.18);
  const scale = Math.max(0.85, 1 - item.dist * 0.06);
  return { transform: `translateY(${item.y}px) scale(${scale})`, opacity };
}

// 触摸/鼠标拖拽选择
let dragType: 'year' | 'month' | null = null;
let dragStartY = 0;
let dragStartOffset = 0;

function offsetOf(type: 'year' | 'month') {
  return type === 'year' ? yearOffset.value : monthOffset.value;
}

function wheelDown(e: PointerEvent, type: 'year' | 'month') {
  dragType = type;
  dragStartY = e.clientY;
  dragStartOffset = offsetOf(type);
  window.addEventListener('pointermove', onWheelMove);
  window.addEventListener('pointerup', onWheelUp);
  window.addEventListener('pointercancel', onWheelUp);
  e.preventDefault();
}

function onWheelMove(e: PointerEvent) {
  if (!dragType) return;
  const o = dragStartOffset - (e.clientY - dragStartY) / ITEM_H;
  if (dragType === 'year') yearOffset.value = o;
  else monthOffset.value = o;
}

function onWheelUp() {
  if (!dragType) return;
  const snapped = Math.round(offsetOf(dragType));
  if (dragType === 'year') yearOffset.value = snapped;
  else monthOffset.value = ((snapped % 12) + 12) % 12; // 取模后回到 [0,12)，避免偏移无限增大
  dragType = null;
  window.removeEventListener('pointermove', onWheelMove);
  window.removeEventListener('pointerup', onWheelUp);
  window.removeEventListener('pointercancel', onWheelUp);
}

// 桌面端鼠标滚轮选择（hover 到对应滚轮时）
function onWheelScroll(e: WheelEvent, type: 'year' | 'month') {
  const cur = Math.round(offsetOf(type));
  const next = cur + (e.deltaY > 0 ? 1 : -1);
  if (type === 'year') yearOffset.value = next;
  else monthOffset.value = ((next % 12) + 12) % 12;
}

const waterfall = ref<any[]>([]);
const waterPage = ref(1);
const totalPage = ref(1);
const pageSize = 15;
const loadingMore = ref(false);
const loadError = ref(false);

// 是否还有下一页可加载（waterPage 指向待加载的页码）
const hasMore = computed(() => waterPage.value <= totalPage.value);

function fmt(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const currentMonthLabel = computed(() => `${currentYear.value}年${currentMonth.value + 1}月`);

const calendarCells = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value, 1);
  const startWeekday = firstDay.getDay();
  const daysInMonth = new Date(currentYear.value, currentMonth.value + 1, 0).getDate();
  const cells: any[] = [];
  const dateSet = new Set(monthDates.value);
  const todayStr = fmt(new Date());
  for (let i = 0; i < startWeekday; i++) cells.push({ key: `blank-${i}`, date: null });
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(currentYear.value, currentMonth.value, d);
    const dateStr = fmt(date);
    cells.push({
      key: dateStr,
      date: dateStr,
      dayNum: d,
      hasMenu: dateSet.has(dateStr),
      isToday: dateStr === todayStr,
      isSelected: dateStr === selectedDate.value
    });
  }
  return cells;
});

async function loadMonth() {
  const month = `${currentYear.value}-${String(currentMonth.value + 1).padStart(2, '0')}`;
  try {
    const res = await menuApi.getMonthDates(month);
    monthDates.value = res.dates;
  } catch (e) {
    console.error('load month failed', e);
  }
}

function shiftMonth(delta: number) {
  const d = new Date(currentYear.value, currentMonth.value + delta, 1);
  currentYear.value = d.getFullYear();
  currentMonth.value = d.getMonth();
  loadMonth();
}

function openDatePicker() {
  yearOffset.value = currentYear.value;
  monthOffset.value = currentMonth.value;
  showDatePicker.value = true;
}

function confirmDatePicker() {
  currentYear.value = pickYear.value;
  currentMonth.value = pickMonth.value;
  showDatePicker.value = false;
  loadMonth();
}

async function selectDay(dateStr: string) {
  selectedDate.value = dateStr;
  try {
    dayMenu.value = await menuApi.getByDate(dateStr);
  } catch (e) {
    console.error('load day failed', e);
  }
}

async function removeFromDay(recipeId: string) {
  try {
    await menuApi.remove(recipeId, selectedDate.value);
    toast('已移除');
    selectDay(selectedDate.value);
    loadMonth();
  } catch (e) {
    console.error('remove failed', e);
  }
}

async function switchWaterfall() {
  mode.value = 'waterfall';
  window.scrollTo(0, 0);
  await loadWaterfall(true);
}

// 加载瀑布流：reset=true 时从第一页重新加载，否则追加下一页
async function loadWaterfall(reset = false) {
  if (loadingMore.value) return;
  if (!reset && !hasMore.value) return;
  loadingMore.value = true;
  loadError.value = false;
  if (reset) {
    waterPage.value = 1;
    totalPage.value = 1;
    waterfall.value = [];
  }
  try {
    const res = await menuApi.getWaterfall({ page: waterPage.value, page_size: pageSize });
    totalPage.value = res.total_page;
    if (reset) {
      waterfall.value = [...res.list];
    } else {
      // 追加并按日期去重，避免数据变动导致重复分组
      const seen = new Set(waterfall.value.map(g => g.date));
      waterfall.value.push(...res.list.filter((g: any) => !seen.has(g.date)));
    }
    if (res.list.length === 0 || waterPage.value >= totalPage.value) {
      waterPage.value = totalPage.value + 1; // 已到底
    } else {
      waterPage.value++;
    }
  } catch (e) {
    console.error('waterfall failed', e);
    loadError.value = true;
  } finally {
    loadingMore.value = false;
    fillViewportIfNeeded();
  }
}

// 滚动接近底部时触发加载下一页
function onScroll() {
  if (mode.value !== 'waterfall') return;
  if (loadingMore.value || !hasMore.value) return;
  const scrollBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
  if (scrollBottom < 100) loadWaterfall(false);
}

// 首屏内容不足一屏时自动补载，保证滚动触发可用
function fillViewportIfNeeded() {
  if (loadingMore.value || loadError.value || !hasMore.value || mode.value !== 'waterfall') return;
  const remaining = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
  if (remaining <= 200) loadWaterfall(false);
}

function goDetail(id: string) {
  router.push(`/recipes/${id}`);
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true });
  loadMonth();
  selectDay(fmt(today));
});

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll);
});
</script>

<style scoped>
.menu { padding: 20px; }
.header { display: flex; justify-content: flex-end; align-items: center; margin-bottom: 16px; }

.mode-switch { display: flex; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
.mode-btn { padding: 8px 16px; border: none; background: white; cursor: pointer; font-size: 14px; }
.mode-btn.active { background: #4a90d9; color: white; }

.calendar-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.month-title { font-size: 1.1rem; font-weight: 600; cursor: pointer; user-select: none; }

.calendar {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
  background: white; border-radius: 12px; padding: 12px; margin-bottom: 16px;
}
.weekday { text-align: center; font-size: 12px; color: #888; padding: 6px 0; }
.day {
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px; cursor: pointer; position: relative; font-size: 14px;
  height: 36px;
}
.day.blank { cursor: default; }
.day.has-menu { background: #fff3cd; }
.day.today { outline: 2px solid #4a90d9; }
.day.selected { background: #4a90d9; color: white; }
.day.has-menu::after {
  content: ''; position: static; transform: none; margin-left: 4px;
  width: 5px; height: 5px; border-radius: 50%; background: #f44336;
}

.date-picker-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 16px;
}
.date-picker {
  background: white; border-radius: 12px; padding: 24px;
  width: 100%; max-width: 420px;
}
.date-picker-title { margin: 0 0 16px 0; text-align: center; }
.picker-wheels { display: flex; gap: 12px; margin-bottom: 20px; }
.wheel {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;
  user-select: none; -webkit-user-select: none;
}
.wheel-mask {
  position: relative; width: 100%; height: 200px; overflow: hidden;
  touch-action: none;
}
.wheel-item {
  position: absolute; left: 0; right: 0; top: 50%;
  height: 40px; line-height: 40px; margin-top: -20px;
  text-align: center; font-size: 17px; color: #333;
  will-change: transform, opacity;
}
.wheel-item.active { color: #4a90d9; font-weight: 600; }
.wheel-center {
  position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%);
  height: 40px; border-top: 1px solid #eee; border-bottom: 1px solid #eee;
  background: rgba(74, 144, 217, 0.06); pointer-events: none;
}
.wheel-caption { font-size: 13px; color: #666; }
.picker-actions { display: flex; justify-content: flex-end; gap: 10px; }

.day-detail { background: white; border-radius: 12px; padding: 16px; }
.day-detail h2 { margin: 0 0 12px 0; font-size: 1.1rem; }
.shopping-list { background: #f9f9f9; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.shopping-list h3 { margin: 0; font-size: 13px; color: #666; white-space: nowrap; }
.shopping-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
.shop-chips { display: flex; flex-wrap: wrap; align-items: center; }
.shop-chip {
  display: inline-block; background: #d4edda; color: #155724; padding: 4px 10px;
  border-radius: 12px; font-size: 12px; margin: 0 4px 4px 0;
}
.shop-chip.sea { background: #fff3cd; color: #856404; }

.day-recipes { display: flex; flex-direction: column; gap: 8px; }
.day-recipe {
  display: flex; justify-content: space-between; align-items: center;
  background: #f9f9f9; border-radius: 8px; padding: 12px;
}
.day-recipe-info { cursor: pointer; flex: 1; }
.recipe-title { font-weight: 500; color: #333; }
.recipe-time { font-size: 12px; color: #999; margin-left: 8px; }
.empty-day { color: #999; text-align: center; padding: 20px; }

.waterfall-group { background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
.waterfall-date { margin: 0 0 12px 0; font-size: 1rem; color: #4a90d9; }
.waterfall-recipes { display: flex; flex-direction: column; gap: 8px; }
.waterfall-recipe {
  background: #f9f9f9; border-radius: 8px; padding: 12px; cursor: pointer;
  display: flex; justify-content: space-between; align-items: center;
}

.load-more { display: flex; justify-content: center; align-items: center; gap: 12px; padding: 20px; color: #999; font-size: 13px; }
.load-more .loading { color: #4a90d9; }
.load-more .error { color: #f44336; }
.load-more .end { color: #bbb; }

.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn-primary { background: #4a90d9; color: white; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-small { padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; min-height: 36px; }
.btn-danger { background: #f44336; color: white; }

.empty-state { text-align: center; padding: 40px 20px; color: #888; }

@media (max-width: 767px) {
  .menu { padding: 16px; }
  .header { flex-direction: column; gap: 12px; align-items: stretch; }
  .mode-switch { width: 100%; }
  .mode-btn { flex: 1; }
  .calendar { padding: 8px; gap: 2px; }
  .day { font-size: 13px; aspect-ratio: 1; height: auto; }
  .day.has-menu::after {
    position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%); margin-left: 0;
  }
  .date-picker-mask { padding: 0; align-items: flex-end; }
  .date-picker { border-radius: 12px 12px 0 0; max-height: 90vh; overflow-y: auto; }
}
</style>
